"""Published wind-curve and spatial-weighting sensitivity helpers."""

import numpy as np
import pandas as pd
import shapely


def cubic_capacity_factor(speed):
    """Original illustrative 3/12/25 m/s curve; preserve float32 evaluation."""
    speed = np.asarray(speed)
    if not np.isfinite(speed).all() or (speed < 0).any():
        raise ValueError("Wind speeds must be finite and nonnegative.")
    return np.where((speed >= 3) & (speed < 12),
                    (speed**3 - 3**3) / (12**3 - 3**3),
                    np.where((speed >= 12) & (speed < 25), 1.0, 0.0))


def published_capacity_factor(speed, curve, cut_in, cut_out):
    speed = np.asarray(speed)
    x = curve["Wind Speed [m/s]"].to_numpy(dtype=float)
    y = curve["Power [-]"].to_numpy(dtype=float)
    if (not np.isfinite(speed).all() or (speed < 0).any()
            or len(x) < 2 or not np.isfinite(x).all() or not np.isfinite(y).all()
            or not (np.diff(x) > 0).all() or not ((y >= 0) & (y <= 1)).all()):
        raise ValueError("Invalid wind speeds or published power curve.")
    if not np.isfinite([cut_in, cut_out]).all() or not x[0] <= cut_in < cut_out <= x[-1]:
        raise ValueError("Operating bounds must lie within the tabulated curve.")
    power = np.interp(speed, x, y, left=0.0, right=0.0)
    # Preserve published values at the cut-in/out endpoints. Do not linearly
    # ramp beyond shutdown, including the IEC III table's 22-to-23 m/s drop.
    return np.where((speed >= cut_in) & (speed <= cut_out), power, 0.0)


def select_eia_inventory(wind, plants, boundary):
    """Select CA onshore OP rows from a fixed EIA-860 2020 snapshot."""
    candidates = wind.loc[
        wind["State"].astype(str).str.strip().eq("CA")
        & wind["Technology"].astype(str).str.strip().eq("Onshore Wind Turbine")
    ].copy()
    if candidates.duplicated(["Plant Code", "Generator ID"]).any():
        raise ValueError("Duplicate plant/generator identifiers in EIA wind data.")
    candidates = candidates.merge(
        plants[["Plant Code", "Latitude", "Longitude"]], on="Plant Code",
        how="left", validate="many_to_one",
    )
    out = candidates.rename(columns={
        "Plant Code": "plant_id", "Generator ID": "generator_id",
        "Plant Name": "plant_name", "Status": "status",
        "Nameplate Capacity (MW)": "capacity_mw", "Latitude": "latitude",
        "Longitude": "longitude", "Operating Year": "operating_year",
        "Operating Month": "operating_month", "Number of Turbines": "turbines",
    })
    for name in ["capacity_mw", "latitude", "longitude"]:
        out[name] = pd.to_numeric(out[name], errors="coerce")
    out["reported_hub_height_m"] = pd.to_numeric(
        out["Turbine Hub Height (Feet)"], errors="coerce") * 0.3048
    out["status"] = out.status.astype(str).str.strip()
    reason = np.full(len(out), "", dtype=object)
    reason[out.status.ne("OP").to_numpy()] = "not_operating_status_OP"
    valid_capacity = np.isfinite(out.capacity_mw) & (out.capacity_mw > 0)
    reason[(reason == "") & ~valid_capacity.to_numpy()] = "invalid_capacity"
    valid_location = (np.isfinite(out.latitude) & np.isfinite(out.longitude)
                      & out.latitude.between(32, 42) & out.longitude.between(-125, -114))
    reason[(reason == "") & ~valid_location.to_numpy()] = "outside_grid_or_invalid_coordinates"
    inside = np.zeros(len(out), dtype=bool)
    usable = np.flatnonzero(valid_location.to_numpy())
    inside[usable] = shapely.intersects_xy(
        boundary, out.longitude.iloc[usable].to_numpy(), out.latitude.iloc[usable].to_numpy())
    reason[(reason == "") & ~inside] = "outside_california_boundary"
    out["exclusion_reason"] = reason
    columns = ["plant_id", "generator_id", "plant_name", "status", "capacity_mw",
               "latitude", "longitude", "operating_year", "operating_month",
               "reported_hub_height_m", "turbines", "exclusion_reason"]
    kept, excluded = out.loc[reason == "", columns].copy(), out.loc[reason != "", columns].copy()
    if kept.empty:
        raise ValueError("Inventory selection retained no operating CA wind generators.")
    kept = kept.drop(columns="exclusion_reason")
    aggregate = kept.groupby("plant_id", as_index=False).agg(
        plant_name=("plant_name", "first"), latitude=("latitude", "first"),
        longitude=("longitude", "first"), capacity_mw=("capacity_mw", "sum"),
        generator_count=("generator_id", "size"),
    )
    known_height = np.isfinite(kept.reported_hub_height_m) & (kept.reported_hub_height_m > 0)
    height_capacity = float(kept.loc[known_height, "capacity_mw"].sum())
    qa = {
        "ca_onshore_candidate_generators": len(out),
        "candidate_capacity_mw": float(out.capacity_mw.sum()),
        "retained_generators": len(kept), "retained_plants": len(aggregate),
        "retained_capacity_mw": float(kept.capacity_mw.sum()),
        "excluded_generators": len(excluded),
        "excluded_capacity_mw": float(excluded.capacity_mw.sum()),
        "exclusion_counts": excluded.exclusion_reason.value_counts().to_dict(),
        "known_hub_height_capacity_mw": height_capacity,
        "capacity_weighted_reported_hub_height_m": (
            float(np.average(kept.loc[known_height, "reported_hub_height_m"],
                             weights=kept.loc[known_height, "capacity_mw"]))
            if height_capacity else None
        ),
    }
    return kept, aggregate, excluded, qa


def capacity_grid_weights(plants, latitude, longitude, mask):
    """Map plant points to the nearest grid center; aggregate MW without cos(lat)."""
    lat, lon, mask = np.asarray(latitude), np.asarray(longitude), np.asarray(mask)
    if mask.shape != (len(lat), len(lon)):
        raise ValueError("Mask and coordinate shapes disagree.")
    if plants.empty or plants.plant_id.duplicated().any():
        raise ValueError("Plant IDs must be unique and the inventory nonempty.")
    capacity = plants.capacity_mw.to_numpy(dtype=float)
    y, x = plants.latitude.to_numpy(dtype=float), plants.longitude.to_numpy(dtype=float)
    if (not np.isfinite(capacity).all() or not (capacity > 0).all()
            or not np.isfinite(y).all() or not np.isfinite(x).all()
            or not ((y >= lat.min()) & (y <= lat.max())).all()
            or not ((x >= lon.min()) & (x <= lon.max())).all()):
        raise ValueError("Plants require valid capacities and coordinates inside the grid.")
    iy = np.abs(y[:, None] - lat[None, :]).argmin(axis=1)
    ix = np.abs(x[:, None] - lon[None, :]).argmin(axis=1)
    grid = np.zeros(mask.shape, dtype=float)
    np.add.at(grid, (iy, ix), capacity)
    assignments = plants.copy()
    assignments["grid_latitude"] = lat[iy]
    assignments["grid_longitude"] = lon[ix]
    assignments["nearest_center_inside_admin_mask"] = mask[iy, ix].astype(bool)
    return grid / grid.sum(), assignments
