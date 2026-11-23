"""Factorial January sensitivity: four curves, two fixed geographic weightings."""

import argparse
import hashlib
import json
from pathlib import Path
import platform
import re

import numpy as np
import pandas as pd
import xarray as xr

from energy_events import combined_window_events, simultaneous_events, utc_hourly_index
from wind_model import capacity_grid_weights, cubic_capacity_factor, published_capacity_factor


def checksum(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", type=Path,
                        default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--tag", default="2020_01")
    parser.add_argument("--headless", action="store_true")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_-]+", args.tag):
        parser.error("Use letters, numbers, underscores or hyphens in tag.")
    project = args.project_dir.resolve()
    raw, reference, processed = [project / p for p in ["data/raw", "data/reference", "data/processed"]]
    tables, figures = project / "results/tables", project / "results/figures"
    for directory in [processed, tables, figures]:
        directory.mkdir(parents=True, exist_ok=True)
    curve_dir = reference / "wind_curves"
    manifest = json.loads((curve_dir / "manifest.json").read_text())
    for name, expected in manifest["files"].items():
        if checksum(curve_dir / name) != expected:
            raise ValueError(f"Reference curve/source checksum mismatch: {name}")
    curves = {name: pd.read_csv(curve_dir / spec["csv"])
              for name, spec in manifest["curves"].items()}
    if any(spec["hub_height"] != 100 for spec in manifest["curves"].values()):
        raise ValueError("This controlled comparison requires 100 m reference curves.")
    wind_path = raw / "data_stream-oper_stepType-instant.nc"
    mask_path = processed / "california_mask.nc"
    with xr.open_dataset(wind_path, engine="netcdf4") as ds, xr.open_dataset(mask_path) as masks:
        ds, mask = xr.align(ds[["u100", "v100"]], masks.california_mask, join="exact")
        for variable in ["u100", "v100"]:
            units = ds[variable].attrs.get("units", "").replace(" ", "")
            if units not in {"ms**-1", "ms-1", "ms^-1", "m/s"}:
                raise ValueError("Expected 100 m wind components in m/s.")
        times = utc_hourly_index(ds.valid_time.values)
        if len(times) < 49:
            raise ValueError("At least 49 snapshots are needed for complete 48h interval means.")
        latitude, longitude = ds.latitude.values, ds.longitude.values
        admin = mask.transpose("latitude", "longitude").values
        if not np.isin(admin, [0, 1]).all() or not admin.any():
            raise ValueError("Administrative mask must be nonempty and binary.")
        speed = np.hypot(ds.u100, ds.v100).transpose("valid_time", "latitude", "longitude").values
    if not np.isfinite(speed).all():
        raise ValueError("Wind inputs contain missing or infinite values.")
    plants_path = reference / "eia2020_ca_wind_plants.csv"
    inventory_metadata_path = reference / "eia2020_ca_wind_metadata.json"
    inventory_metadata = json.loads(inventory_metadata_path.read_text())
    for name, expected in inventory_metadata["derived_files_sha256"].items():
        if checksum(reference / name) != expected:
            raise ValueError(f"Inventory extraction checksum mismatch: {name}")
    plants = pd.read_csv(plants_path)
    capacity_weights, assignments = capacity_grid_weights(plants, latitude, longitude, admin)
    uniform_weights = np.cos(np.deg2rad(latitude))[:, None] * admin
    uniform_weights = uniform_weights / uniform_weights.sum()
    weights = {"uniform": uniform_weights, "eia2020": capacity_weights}
    assignments.to_csv(tables / f"wind_assessment_site_assignments_{args.tag}.csv", index=False)
    yy, xx = np.meshgrid(latitude, longitude, indexing="ij")
    grid = pd.DataFrame({
        "latitude": yy.ravel(), "longitude": xx.ravel(), "inside_admin_mask": admin.ravel().astype(bool),
        "uniform_area_weight": uniform_weights.ravel(), "eia2020_capacity_weight": capacity_weights.ravel(),
    })
    grid.to_csv(tables / f"wind_assessment_grid_weights_{args.tag}.csv", index=False)
    snapshot = pd.DataFrame(index=times)
    for name in ["cubic", *curves]:
        if name == "cubic":
            field = cubic_capacity_factor(speed)
        else:
            spec = manifest["curves"][name]
            field = published_capacity_factor(speed, curves[name],
                                             spec["cut_in_wind_speed"], spec["cut_out_wind_speed"])
        for weighting, weight in weights.items():
            snapshot[f"{name}_{weighting}"] = np.einsum("tij,ij->t", field, weight, optimize=True)
    if not np.isfinite(snapshot.to_numpy()).all() or not ((snapshot >= 0) & (snapshot <= 1)).all().all():
        raise ValueError("Invalid weighted wind capacity factors.")
    hourly = (snapshot.iloc[:-1].to_numpy() + snapshot.iloc[1:].to_numpy()) / 2
    hourly = pd.DataFrame(hourly, index=times[1:], columns=snapshot.columns)
    snapshot.to_csv(processed / f"wind_assessment_snapshots_{args.tag}.csv", index_label="time_utc")
    hourly.to_csv(processed / f"wind_assessment_{args.tag}.csv", index_label="interval_end_utc")

    pv_path = processed / f"pv_ac_capacity_factor_{args.tag}.csv"
    pv = pd.read_csv(pv_path, index_col=0)
    pv.index = pd.to_datetime(pv.index, utc=True)
    if not pv.index.equals(hourly.index):
        raise ValueError("PV and complete wind interval labels disagree.")
    summary_rows, sensitivity_rows, reference_catalogues, window_catalogues = [], [], [], []
    for scenario in hourly:
        resources = pd.DataFrame({"wind_cf": hourly[scenario], "pv_cf": pv.pv_ac_capacity_factor})
        low, periods = simultaneous_events(resources)
        ref_events = periods.loc[periods.meets_minimum_duration]
        baseline_diagnostic, baseline_events = combined_window_events(resources)
        summary_rows.append({
            "wind_scenario": scenario, "snapshot_mean_cf": snapshot[scenario].mean(),
            "hourly_mean_cf": hourly[scenario].mean(), "hourly_max_cf": hourly[scenario].max(),
            "simultaneous_low_hours": int(low.sum()), "reference_events_at_least_24h": len(ref_events),
            "minimum_48h_combined_cf_50pct_wind": baseline_diagnostic.rolling_mean_cf.min(),
            "combined_48h_events_at_006_50pct_wind": len(baseline_events),
            "complete_combined_events_at_006_50pct_wind": int((~baseline_events.boundary_context_incomplete).sum()),
        })
        reference_catalogues.append(periods.assign(wind_scenario=scenario))
        for share in [0.25, 0.50, 0.75]:
            for threshold in [0.05, 0.06, 0.10]:
                diagnostic, events = combined_window_events(resources, share, threshold)
                sensitivity_rows.append({
                    "wind_scenario": scenario, "wind_rated_capacity_share": share,
                    "combined_cf_threshold": threshold, "qualifying_windows": int(diagnostic.qualifying_window_endpoint.sum()),
                    "covered_hours": int(diagnostic.covered_by_qualifying_window.sum()),
                    "observed_events": len(events),
                    "complete_events": int((~events.boundary_context_incomplete).sum()),
                    "edge_context_uncertain_events": int(events.boundary_context_incomplete.sum()),
                })
                window_catalogues.append(events.assign(wind_scenario=scenario,
                    wind_rated_capacity_share=share, combined_cf_threshold=threshold))
    summary = pd.DataFrame(summary_rows)
    summary.to_csv(tables / f"wind_assessment_summary_{args.tag}.csv", index=False)
    pd.DataFrame(sensitivity_rows).to_csv(tables / f"wind_assessment_event_sensitivity_{args.tag}.csv", index=False)
    pd.concat(reference_catalogues, ignore_index=True).to_csv(tables / f"wind_assessment_reference_periods_{args.tag}.csv", index=False)
    pd.concat(window_catalogues, ignore_index=True).to_csv(tables / f"wind_assessment_48h_events_{args.tag}.csv", index=False)
    outside = ~assignments.nearest_center_inside_admin_mask
    metadata = {
        "status": "Controlled curve/location sensitivity, not observed generation validation",
        "wind_height_m": 100, "density_wake_availability_losses": "Not explicitly modeled",
        "inventory": "Fixed 2020 annual EIA OP plant layout; not actual January fleet availability",
        "uniform_weighting": "Cos(latitude) per selected administrative grid center",
        "capacity_weighting": "Plant wind nameplate MW aggregated at nearest ERA5 center; no extra latitude factor",
        "nearest_center_tie_rule": "First coordinate in ERA5 file order",
        "pv_assumption": "Existing 35-degree PV scenario held fixed with its original uniform area weights",
        "event_assumptions": "Hourly each <0.20 for >=24h; 48h combined windows at 0.05/0.06/0.10 and 25/50/75% wind shares",
        "input_snapshots": len(times), "complete_intervals": len(hourly),
        "administrative_grid_centers": int(admin.sum()),
        "capacity_weighted_grid_centers": int((capacity_weights > 0).sum()),
        "mapped_plants": len(plants), "mapped_capacity_mw": float(plants.capacity_mw.sum()),
        "plants_nearest_to_outside_admin_centers": int(outside.sum()),
        "capacity_nearest_to_outside_admin_centers_mw": float(assignments.loc[outside, "capacity_mw"].sum()),
        "power_curve_archive_commit": manifest["commit"],
        "python": platform.python_version(),
        "inputs": [{"path": str(p.relative_to(project)), "sha256": checksum(p)} for p in
                   [wind_path, mask_path, plants_path, inventory_metadata_path,
                    pv_path, curve_dir / "manifest.json"]],
    }
    (tables / f"wind_assessment_metadata_{args.tag}.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8")

    if args.headless:
        import matplotlib
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 2, figsize=(13, 9))
    speeds = np.linspace(0, 27, 1081)
    axes[0, 0].plot(speeds, cubic_capacity_factor(speeds), label="Original cubic", linestyle="--")
    for name, curve in curves.items():
        spec = manifest["curves"][name]
        axes[0, 0].plot(speeds, published_capacity_factor(speeds, curve,
                        spec["cut_in_wind_speed"], spec["cut_out_wind_speed"]), label=name)
    axes[0, 0].set(xlabel="100 m wind speed (m/s)", ylabel="Capacity factor", title="Curve assumptions")
    axes[0, 0].legend(fontsize=8)
    axes[0, 1].scatter(xx[admin.astype(bool)], yy[admin.astype(bool)], s=2, color="lightgray")
    occupied = capacity_weights > 0
    axes[0, 1].scatter(xx[occupied], yy[occupied], s=capacity_weights[occupied] * 2500,
                       alpha=0.5, label="MW-weighted grid cells")
    axes[0, 1].scatter(plants.longitude, plants.latitude, s=5, marker="x", color="tab:red", label="EIA wind plant points")
    axes[0, 1].set(xlabel="Longitude", ylabel="Latitude", title="Fixed 2020 capacity locations")
    axes[0, 1].set_aspect(1 / np.cos(np.deg2rad(37)))
    axes[0, 1].legend(fontsize=8)
    for name in ["cubic_uniform", "wtk_iec2_uniform", "cubic_eia2020", "wtk_iec2_eia2020"]:
        axes[1, 0].plot(hourly.index, hourly[name], label=name, linewidth=0.8)
    axes[1, 0].set(xlabel="Interval end (UTC)", ylabel="Wind capacity factor", title="Separating curve and location effects")
    axes[1, 0].legend(fontsize=7)
    axes[1, 0].tick_params(axis="x", labelrotation=25)
    names = ["cubic", *curves]
    x = np.arange(len(names))
    for offset, weighting in [(-0.18, "uniform"), (0.18, "eia2020")]:
        means = [hourly[f"{name}_{weighting}"].mean() for name in names]
        axes[1, 1].bar(x + offset, means, width=0.36, label=weighting)
    axes[1, 1].set(xticks=x, xticklabels=["Cubic", "WTK I", "WTK II", "WTK III"],
                   ylabel="Mean wind CF over 743 intervals", title="January scenario means")
    axes[1, 1].legend(fontsize=8)
    for ax in axes.ravel():
        ax.grid(alpha=0.15)
    fig.tight_layout()
    fig.savefig(figures / f"wind_model_geography_assessment_{args.tag}.png", dpi=200, bbox_inches="tight")
    if not args.headless:
        plt.show()
    plt.close(fig)
    print(summary.to_string(index=False))
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
