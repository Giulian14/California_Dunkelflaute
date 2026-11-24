"""Carry weather brackets across files, then detect events on compact joined series."""

import numpy as np
import pandas as pd
import xarray as xr

from energy_events import utc_hourly_index, validate_resources
from pv_model import PVConfig, model_cell, prepare_forcing
from wind_model import cubic_capacity_factor


def interval_weather_pairs(pairs, mask):
    """Yield weather blocks with one preceding snapshot, once per global record.

    Input files must be ordered, consecutive and nonoverlapping. The global
    initial snapshot supplies a bracket, not a complete preceding interval.
    Hourly ERA5 ssrd accumulation semantics must already be established.
    """
    previous_i = previous_a = None
    produced = False
    for instant, accum in pairs:
        instant = instant[["u100", "v100", "t2m"]]
        accum = accum[["ssrd"]]
        instant, accum, _ = xr.align(instant, accum, mask, join="exact")
        index = utc_hourly_index(instant.valid_time.values)
        for name in ["u100", "v100"]:
            units = instant[name].attrs.get("units", "").replace(" ", "")
            if units not in {"ms**-1", "ms-1", "ms^-1", "m/s"}:
                raise ValueError("Expected 100 m wind components in m/s.")
            if instant[name].attrs.get("GRIB_uvRelativeToGrid") != 0:
                raise ValueError("Require an explicitly unrotated wind grid.")
        if previous_i is not None:
            last = utc_hourly_index(previous_i.valid_time.values)[-1]
            if index[0] != last + pd.Timedelta(hours=1):
                raise ValueError("Weather files must be consecutive and nonoverlapping.")
            for current, prior in [(instant, previous_i), (accum, previous_a)]:
                for name in current.data_vars:
                    if (current[name].dtype != prior[name].dtype
                            or current[name].attrs.get("units") != prior[name].attrs.get("units")):
                        raise ValueError("Weather dtype/units changed across files.")
            instant = xr.concat([previous_i, instant], dim="valid_time", data_vars="all",
                                coords="minimal", compat="equals", join="exact", combine_attrs="override")
            accum = xr.concat([previous_a, accum], dim="valid_time", data_vars="all",
                              coords="minimal", compat="equals", join="exact", combine_attrs="override")
        # Deep-copy only the final record; do not retain a month's array buffer.
        previous_i = instant.isel(valid_time=slice(-1, None)).copy(deep=True)
        previous_a = accum.isel(valid_time=slice(-1, None)).copy(deep=True)
        if instant.sizes["valid_time"] > 1:
            produced = True
            yield instant, accum
    if not produced:
        raise ValueError("At least two global snapshots are needed for a complete interval.")


def interval_weather_files(paths, mask):
    """Load one NetCDF pair at a time; generator consumers release each block."""
    def pairs():
        for instant_path, accum_path in paths:
            with xr.open_dataset(instant_path, engine="netcdf4") as instant, xr.open_dataset(accum_path, engine="netcdf4") as accum:
                yield instant.load(), accum.load()
    yield from interval_weather_pairs(pairs(), mask)


def model_resource_block(instant, accum, mask):
    """Preserved cubic/uniform wind and 35-degree PV; no model refitting."""
    forcing = prepare_forcing(instant, accum, mask)
    selected = mask.transpose("latitude", "longitude").values.astype(bool)
    speed = np.hypot(instant.u100, instant.v100).transpose("valid_time", "latitude", "longitude").values[:, selected]
    snapshot = cubic_capacity_factor(speed) @ forcing["weights"]
    wind = (snapshot[:-1] + snapshot[1:]) / 2
    pv = np.zeros(len(wind))
    config = PVConfig()
    for cell, weight in enumerate(forcing["weights"]):
        result = model_cell(forcing["interval_end"], forcing["ghi"][:, cell], forcing["temp_air"][:, cell],
                            forcing["latitude"][cell], forcing["longitude"][cell], config)
        pv += result.pv_ac_capacity_factor.to_numpy() * weight
    result = pd.DataFrame({"wind_cf": wind, "pv_cf": pv}, index=forcing["interval_end"])
    result.index.name = "interval_end_utc"
    validate_resources(result)
    return result


def join_resource_chunks(chunks):
    """Join compact modeled intervals before ANY rolling/event calculations.

    A 20-year two-resource float64 table contains about 2.8 MB of values.
    Concatenating it avoids resetting event state at arbitrary file edges.
    """
    pieces = []
    schema = None
    for frame in chunks:
        if (not isinstance(frame.index, pd.DatetimeIndex) or frame.index.tz is None
                or frame.empty or not np.isfinite(frame.to_numpy(dtype=float)).all()):
            raise ValueError("Chunks need finite data and explicit, nonempty time-aware indices.")
        frame = frame.astype(float).copy()
        frame.index = utc_hourly_index(frame.index)
        validate_resources(frame)
        if schema is None:
            schema = list(frame.columns)
        if list(frame.columns) != schema:
            raise ValueError("Resource column schema changed across chunks.")
        if pieces and frame.index[0] != pieces[-1].index[-1] + pd.Timedelta(hours=1):
            raise ValueError("Resource chunks must be consecutive, ordered and nonoverlapping.")
        pieces.append(frame)
    if not pieces:
        raise ValueError("No resource intervals supplied.")
    result = pd.concat(pieces)
    validate_resources(result)
    return result
