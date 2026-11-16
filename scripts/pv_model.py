"""Fixed-tilt PV scenario using ERA5 GHI, Ross temperature and PVWatts.

This is a representative system, not a calibrated California fleet model.
See docs/pv_model.md for interval conventions and modeling limitations.
"""

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd
import pvlib
import xarray as xr


@dataclass(frozen=True)
class PVConfig:
    tilt_deg: float = 35.0
    azimuth_deg: float = 180.0
    albedo: float = 0.20
    noct_c: float = 45.0
    gamma_pdc_per_c: float = -0.004
    dc_ac_ratio: float = 1.20
    other_loss_fraction: float = 0.14
    inverter_efficiency: float = 0.96

    def __post_init__(self):
        if not all(np.isfinite(value) for value in asdict(self).values()):
            raise ValueError("PV parameters must be finite.")
        if not 0 <= self.tilt_deg <= 90 or not 0 <= self.azimuth_deg < 360:
            raise ValueError("Invalid panel orientation.")
        if not 0 <= self.albedo <= 1 or not 0 <= self.other_loss_fraction < 1:
            raise ValueError("Invalid albedo or loss fraction.")
        if not 20 < self.noct_c < 100 or not -0.02 < self.gamma_pdc_per_c <= 0:
            raise ValueError("Invalid temperature-model parameter.")
        if self.dc_ac_ratio <= 0 or not 0 < self.inverter_efficiency <= 1:
            raise ValueError("Invalid capacity ratio or inverter efficiency.")


def hourly_utc(times):
    """Validate complete, consecutive hourly ERA5 timestamps; interpret as UTC."""
    index = pd.DatetimeIndex(times)
    if len(index) < 2 or index.hasnans:
        raise ValueError("At least two valid hourly timestamps are required.")
    index = index.tz_localize("UTC") if index.tz is None else index.tz_convert("UTC")
    if not ((index[1:] - index[:-1]) == pd.Timedelta(hours=1)).all():
        raise ValueError("Timestamps must be consecutive and strictly hourly.")
    return index


def prepare_forcing(instant, accum, mask):
    """Return complete-hour, selected-cell forcings with fixed spatial weights."""
    instant, accum, mask = xr.align(
        instant[["t2m"]], accum[["ssrd"]],
        mask.transpose("latitude", "longitude"), join="exact",
    )
    times = hourly_utc(instant["valid_time"].values)
    radiation_units = accum["ssrd"].attrs.get("units", "").replace(" ", "")
    if radiation_units not in {"Jm**-2", "Jm-2", "Jm^-2", "J/m^2", "J/m2"}:
        raise ValueError("Expected hourly ERA5 ssrd in J/m².")
    if instant["t2m"].attrs.get("units", "").lower() not in {"k", "kelvin"}:
        raise ValueError("Expected ERA5 t2m in kelvin.")
    values = np.asarray(mask.values)
    if not np.isin(values, [0, 1]).all() or not values.any():
        raise ValueError("Mask must contain only 0/1 and select at least one cell.")
    selected = values.astype(bool)
    lat, lon = np.meshgrid(instant.latitude.values, instant.longitude.values,
                          indexing="ij")
    latitude, longitude = lat[selected], lon[selected]
    if not ((np.abs(latitude) < 90).all() and (np.abs(longitude) <= 180).all()):
        raise ValueError("Invalid latitude/longitude coordinates.")
    dims = ("valid_time", "latitude", "longitude")
    energy = np.asarray(accum["ssrd"].transpose(*dims).values, dtype=float)[:, selected]
    temperature = np.asarray(instant["t2m"].transpose(*dims).values, dtype=float)[:, selected]
    if not np.isfinite(energy).all() or not np.isfinite(temperature).all():
        raise ValueError("Selected-cell forcings contain missing/infinite values.")
    if (energy < -1.0).any():
        raise ValueError("Unexpected negative solar accumulation below -1 J/m².")
    # t2m snapshots bracket each complete interval; the first ssrd interval
    # lacks its preceding temperature snapshot, so exclude it explicitly.
    weights = np.cos(np.deg2rad(latitude))
    weights /= weights.sum()
    return {
        "interval_end": times[1:],
        "ghi": np.maximum(energy[1:], 0.0) / 3600.0,
        "temp_air": (temperature[:-1] + temperature[1:]) / 2.0 - 273.15,
        "latitude": latitude, "longitude": longitude, "weights": weights,
        "tiny_negative_accumulations_clipped": int((energy[1:] < 0).sum()),
    }


def power_from_poa(poa, temp_air, config):
    """Return AC CF (rated AC denominator = 1 W) and cell temperature."""
    poa, temp_air = np.broadcast_arrays(
        np.asarray(poa, dtype=float), np.asarray(temp_air, dtype=float)
    )
    if not np.isfinite(poa).all() or not np.isfinite(temp_air).all() or (poa < 0).any():
        raise ValueError("POA and temperature must be finite, with POA >= 0.")
    temp_cell = pvlib.temperature.ross(poa, temp_air, noct=config.noct_c)
    # Array DC STC rating = dc_ac_ratio * 1 W AC. Inverter pdc0 is a
    # DIFFERENT quantity: its DC input at rated AC / nominal efficiency.
    pdc = pvlib.pvsystem.pvwatts_dc(
        poa, temp_cell, pdc0=config.dc_ac_ratio,
        gamma_pdc=config.gamma_pdc_per_c, temp_ref=25.0,
    )
    pdc = np.maximum(pdc, 0.0) * (1.0 - config.other_loss_fraction)
    ac = pvlib.inverter.pvwatts(
        pdc, pdc0=1.0 / config.inverter_efficiency,
        eta_inv_nom=config.inverter_efficiency,
    )
    return np.clip(ac, 0.0, 1.0), temp_cell


def model_cell(interval_end, ghi, temp_air, latitude, longitude, config):
    """Model one cell before spatial aggregation; return end-labeled values."""
    times = pd.DatetimeIndex(interval_end)
    if times.tz is None or times.hasnans or len(times) == 0:
        raise ValueError("Use valid, timezone-aware interval-end timestamps.")
    times = times.tz_convert("UTC")
    ghi, temp_air = np.asarray(ghi, dtype=float), np.asarray(temp_air, dtype=float)
    if ghi.shape != (len(times),) or temp_air.shape != ghi.shape:
        raise ValueError("Cell inputs must be one-dimensional and time-aligned.")
    if not np.isfinite(ghi).all() or not np.isfinite(temp_air).all() or (ghi < 0).any():
        raise ValueError("Cell inputs must be finite, with GHI >= 0.")
    midpoint = times - pd.Timedelta(minutes=30)
    position = pvlib.solarposition.get_solarposition(
        midpoint, latitude, longitude, altitude=0.0,
        pressure=101325.0, temperature=temp_air, method="nrel_numpy",
    )
    zenith = position["zenith"].to_numpy()
    # Erbs accepts day-of-year arrays, avoiding deprecated pandas aliases.
    components = pvlib.irradiance.erbs(ghi, zenith, midpoint.day_of_year.to_numpy())
    dni = np.asarray(components["dni"])
    dhi = np.asarray(components["dhi"])
    # An interval can contain daylight even if its midpoint is near/below
    # the horizon. Preserve measured GHI as diffuse rather than deleting it
    # or inventing an unstable direct beam at very low sun angles.
    low_sun = zenith >= 87.0
    dni = np.where(low_sun, 0.0, dni)
    dhi = np.where(low_sun, ghi, dhi)
    poa = pvlib.irradiance.get_total_irradiance(
        config.tilt_deg, config.azimuth_deg, zenith,
        position["azimuth"].to_numpy(), dni, ghi, dhi,
        albedo=config.albedo, model="isotropic",
    )["poa_global"]
    poa = np.maximum(np.asarray(poa), 0.0)
    ac, temp_cell = power_from_poa(poa, temp_air, config)
    result = pd.DataFrame({
        "pv_ac_capacity_factor": ac,
        "ghi_reference_proxy": np.clip(ghi / 1000.0, 0.0, 1.0),
        "poa_global_w_m2": poa, "cell_temperature_c": temp_cell,
        "solar_zenith_deg": zenith,
    }, index=times)
    if not np.isfinite(result.to_numpy()).all():
        raise ValueError("PV model produced nonfinite values.")
    return result
