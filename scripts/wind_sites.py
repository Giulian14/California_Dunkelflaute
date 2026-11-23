"""Capacity-consistency and grid sampling checks for wind-site diagnostics."""

import numpy as np
import pandas as pd
import xarray as xr


def turbine_capacity_audit(generators, annual):
    keys = ["plant_id", "generator_id"]
    if generators.duplicated(keys).any() or annual.duplicated(keys).any():
        raise ValueError("Generator source keys must be unique.")
    audit = generators.merge(annual, on=keys, how="left", validate="one_to_one", indicator=True)
    audit["annual_capacity_consistent"] = audit._merge.eq("both") & np.isclose(
        audit.capacity_mw, audit.annual_capacity_mw, rtol=0, atol=1e-6)
    audit["whole_plant_capacity_consistent"] = audit.groupby("plant_id").annual_capacity_consistent.transform("all")
    return audit


def sample_wind(ds, plants, method):
    """Interpolate u/v at points before hypot; never average speed magnitudes."""
    if method not in {"nearest", "bilinear"}:
        raise ValueError("Use nearest or bilinear sampling.")
    lat, lon = ds.latitude.values, ds.longitude.values
    for axis in [lat, lon]:
        if (len(axis) < 2 or not np.isfinite(axis).all()
                or not ((np.diff(axis) > 0).all() or (np.diff(axis) < 0).all())):
            raise ValueError("Grid axes must be finite and strictly monotonic.")
    y, x = plants.latitude.to_numpy(dtype=float), plants.longitude.to_numpy(dtype=float)
    if (not np.isfinite(y).all() or not np.isfinite(x).all()
            or not ((lat.min() <= y) & (y <= lat.max())).all()
            or not ((lon.min() <= x) & (x <= lon.max())).all()):
        raise ValueError("Require finite plant coordinates inside the grid.")
    if not all(np.isfinite(ds[v].values).all() for v in ["u100", "v100"]):
        raise ValueError("Wind fields contain missing values.")
    iy = np.abs(y[:, None] - lat[None, :]).argmin(axis=1)
    ix = np.abs(x[:, None] - lon[None, :]).argmin(axis=1)
    if method == "nearest":
        u, v = [ds[name].transpose("valid_time", "latitude", "longitude").values[:, iy, ix]
                for name in ["u100", "v100"]]
    else:
        points = ds[["u100", "v100"]].interp(
            latitude=xr.DataArray(y, dims="plant"), longitude=xr.DataArray(x, dims="plant"), method="linear")
        u, v = [points[name].transpose("valid_time", "plant").values for name in ["u100", "v100"]]
    return np.hypot(u, v), iy, ix


def distance_km(lat1, lon1, lat2, lon2):
    """Spherical great-circle diagnostic, mean Earth radius 6371.0088 km."""
    a, b, c, d = np.deg2rad([np.asarray(x, dtype=float) for x in [lat1, lon1, lat2, lon2]])
    h = np.sin((c-a)/2)**2 + np.cos(a)*np.cos(c)*np.sin((d-b)/2)**2
    return 2 * 6371.0088 * np.arcsin(np.sqrt(np.clip(h, 0, 1)))
