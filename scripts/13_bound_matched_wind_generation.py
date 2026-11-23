"""Compare plant-matched January net energy with bounded reference wind output."""

import argparse
import hashlib
import json
from pathlib import Path
import platform

import numpy as np
import pandas as pd
import xarray as xr

from energy_events import utc_hourly_index
from january_wind import monthly_bounds
from wind_model import capacity_grid_weights, cubic_capacity_factor, published_capacity_factor


def checksum(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--wind-data", type=Path)
    parser.add_argument("--mask", type=Path)
    parser.add_argument("--headless", action="store_true")
    args = parser.parse_args()
    project = args.project_dir.resolve()
    raw, reference, processed = [project / p for p in ["data/raw", "data/reference", "data/processed"]]
    tables, figures = project / "results/tables", project / "results/figures"
    for directory in [processed, tables, figures]:
        directory.mkdir(parents=True, exist_ok=True)
    inventory_metadata_path = reference / "jan2020_wind_inventory_metadata.json"
    inventory_meta = json.loads(inventory_metadata_path.read_text())
    for name, expected in inventory_meta["artifacts_sha256"].items():
        if checksum(project / name) != expected:
            raise ValueError(f"Inventory artifact checksum mismatch: {name}")
    plants_path = reference / "jan2020_wind_matched_plants.csv"
    plants = pd.read_csv(plants_path)
    if plants.observed_cf_outside_0_1.any():
        raise ValueError("Observed plant CF outside [0,1]; investigate nominal capacity before comparison.")
    wind_path = args.wind_data or raw / "data_stream-oper_stepType-instant.nc"
    mask_path = args.mask or processed / "california_mask.nc"
    with xr.open_dataset(wind_path, engine="netcdf4") as ds, xr.open_dataset(mask_path) as masks:
        ds, mask = xr.align(ds[["u100", "v100"]], masks.california_mask, join="exact")
        for name in ["u100", "v100"]:
            units = ds[name].attrs.get("units", "").replace(" ", "")
            if units not in {"ms**-1", "ms-1", "ms^-1", "m/s"}:
                raise ValueError("Expected 100 m wind components in m/s.")
        times = utc_hourly_index(ds.valid_time.values)
        latitude, longitude = ds.latitude.values, ds.longitude.values
        admin = mask.transpose("latitude", "longitude").values
        if not np.isin(admin, [0, 1]).all():
            raise ValueError("Expected binary administrative mask.")
        speed = np.hypot(ds.u100, ds.v100).transpose("valid_time", "latitude", "longitude").values
    if not np.isfinite(speed).all():
        raise ValueError("Missing wind values.")
    weights, assignments = capacity_grid_weights(plants, latitude, longitude, admin)
    iy = np.abs(plants.latitude.to_numpy()[:, None] - latitude[None, :]).argmin(axis=1)
    ix = np.abs(plants.longitude.to_numpy()[:, None] - longitude[None, :]).argmin(axis=1)
    point_speed = speed[:, iy, ix]
    capacity = plants.capacity_mw.to_numpy()
    capacity_total = float(capacity.sum())
    observed_total = float(plants.january_net_generation_mwh.sum())
    observed_cf = observed_total / (capacity_total * 744)
    curve_dir = reference / "wind_curves"
    manifest_path = curve_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    for name, expected in manifest["files"].items():
        if checksum(curve_dir / name) != expected:
            raise ValueError("Published source-curve checksum mismatch.")
    if any(spec["hub_height"] != 100 for spec in manifest["curves"].values()):
        raise ValueError("This controlled comparison requires 100 m reference curves.")
    expected = pd.date_range("2020-01-01T09:00Z", "2020-02-01T08:00Z", freq="h")
    keep = times[1:].isin(expected)
    interval_ends = times[1:][keep]
    summary, per_plant, series = [], [], pd.DataFrame(index=interval_ends)
    for name in ["cubic", *manifest["curves"]]:
        if name == "cubic":
            power = cubic_capacity_factor(point_speed)
        else:
            spec = manifest["curves"][name]
            power = published_capacity_factor(point_speed, pd.read_csv(curve_dir / spec["csv"]),
                                              spec["cut_in_wind_speed"], spec["cut_out_wind_speed"])
        hourly = ((power[:-1].astype(float) + power[1:].astype(float)) / 2)[keep]
        aggregate = hourly @ (capacity / capacity_total)
        series[name] = aggregate
        bounds = monthly_bounds(aggregate, interval_ends, capacity_total)
        shortfall = observed_total - bounds["monthly_energy_upper_bound_mwh"]
        summary.append({"curve": name, "plants": len(plants), "capacity_mw": capacity_total,
            "observed_monthly_net_generation_mwh": observed_total,
            "observed_monthly_cf_nominal": observed_cf, **bounds,
            "observed_minus_model_upper_mwh": shortfall,
            "minimum_shortfall_fraction_of_observed": max(0., shortfall) / observed_total,
            "observed_above_model_upper_bound": observed_total > bounds["monthly_energy_upper_bound_mwh"]})
        for n, plant in enumerate(plants.itertuples()):
            per_plant.append({"curve": name, "plant_id": plant.plant_id, "capacity_mw": plant.capacity_mw,
                "observed_monthly_net_generation_mwh": plant.january_net_generation_mwh,
                "observed_monthly_cf_nominal": plant.observed_monthly_cf_nominal,
                **monthly_bounds(hourly[:, n], interval_ends, plant.capacity_mw)})
    assignments_path = tables / "matched_january_wind_site_assignments_2020_01.csv"
    assignments.to_csv(assignments_path, index=False)
    series_path = processed / "matched_january_wind_known_hours_2020_01.csv"
    series.to_csv(series_path, index_label="interval_end_utc")
    summary = pd.DataFrame(summary)
    summary_path = tables / "matched_january_wind_bounds_2020_01.csv"
    summary.to_csv(summary_path, index=False)
    plant_path = tables / "matched_january_wind_plant_bounds_2020_01.csv"
    pd.DataFrame(per_plant).to_csv(plant_path, index=False)
    if args.headless:
        import matplotlib
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(10, 5))
    low, high = summary.monthly_cf_lower_bound.to_numpy(), summary.monthly_cf_upper_bound.to_numpy()
    mid = (low + high) / 2
    ax.errorbar(np.arange(4), mid, yerr=np.vstack([mid-low, high-mid]), fmt="none", capsize=8,
                label="Model bounds: missing hours independently allowed CF 0–1")
    ax.axhline(observed_cf, color="black", linestyle="--", label="EIA plant-matched net energy / nominal MW / 744 h")
    ax.set_xticks(np.arange(4), summary.curve)
    ax.set(ylabel="January capacity factor", title="January 2020 — matched wind plants, fixed nominal capacity")
    ax.set_ylim(bottom=0)
    ax.grid(alpha=.2)
    ax.legend(fontsize=9, loc="lower right")
    fig.text(.5, .01, "Bounds cover missing hours only; snapshot, curve, height and reporting uncertainties remain.", ha="center", fontsize=9)
    fig.tight_layout(rect=[0, .04, 1, 1])
    figure_path = figures / "matched_january_wind_bounds_2020_01.png"
    fig.savefig(figure_path, dpi=180)
    plt.close(fig)
    metadata = {
        "status": "Plant-matched nominal-capacity diagnostic with bounded missing hours; not a calibrated fleet model",
        "python": platform.python_version(), "wind_height_m": 100,
        "cohort_plants": len(plants), "capacity_mw": capacity_total,
        "nominal_month_hours": 744, "known_hours": len(series), "missing_hours": len(expected) - len(series),
        "time_assumption": "EIA January calendar-month energy assigned to Pacific January for CA plants; model preceding-hour interval ends converted to that support",
        "missing_hour_method": "No imputation: lower energy = known hourly CF sum * MW; upper = (known CF sum + missing hours) * MW",
        "weighting": "Nominal capacity at each whole plant's nearest ERA5 center, no extra latitude factor",
        "occupied_grid_centers": int((weights > 0).sum()),
        "nearest_centers_outside_mask": int((~assignments.nearest_center_inside_admin_mask).sum()),
        "known_hour_wind_method": "Curve at each mapped center then average adjacent wind CF snapshots exactly once",
        "limits": ["Stable monthly snapshots do not establish hourly availability or exclude unreported changes",
                   "Reference curves at 100 m; actual hubs/turbines and ERA5 terrain differ",
                   "No density, wake, availability or curtailment corrections; EIA energy is net generation",
                   "Missing-hour bounds are not total confidence intervals or bounds on all model error",
                   "No model selection or fit based on these observations; no solar or event reclassification"],
        "input_sha256": {"wind_NetCDF": checksum(wind_path), "mask_NetCDF": checksum(mask_path),
            str(plants_path.relative_to(project)): checksum(plants_path),
            str(inventory_metadata_path.relative_to(project)): checksum(inventory_metadata_path),
            str(manifest_path.relative_to(project)): checksum(manifest_path)},
        "artifacts_sha256": {str(p.relative_to(project)): checksum(p) for p in
                              [assignments_path, series_path, summary_path, plant_path, figure_path]},
    }
    (tables / "matched_january_wind_metadata_2020_01.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
