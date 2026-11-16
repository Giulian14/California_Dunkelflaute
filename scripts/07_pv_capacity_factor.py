"""Run the fixed-tilt PV scenario on existing ERA5 files. No downloads."""

import argparse
from dataclasses import asdict
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import platform
import re

import numpy as np
import pandas as pd
import xarray as xr

from pv_model import PVConfig, model_cell, prepare_forcing


def sha256(path):
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", type=Path,
                        default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--tag", default="2020_01")
    parser.add_argument("--tilt-deg", type=float, default=35.0)
    parser.add_argument("--dc-ac-ratio", type=float, default=1.20)
    parser.add_argument("--noct-c", type=float, default=45.0)
    parser.add_argument("--loss-fraction", type=float, default=0.14)
    parser.add_argument("--headless", action="store_true")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_-]+", args.tag):
        parser.error("tag must contain only letters, numbers, underscores or hyphens")
    config = PVConfig(
        tilt_deg=args.tilt_deg, dc_ac_ratio=args.dc_ac_ratio,
        noct_c=args.noct_c, other_loss_fraction=args.loss_fraction,
    )
    project = args.project_dir.resolve()
    inputs = [
        project / "data/raw/data_stream-oper_stepType-instant.nc",
        project / "data/raw/data_stream-oper_stepType-accum.nc",
        project / "data/processed/california_mask.nc",
    ]
    with (
        xr.open_dataset(inputs[0], engine="netcdf4") as instant,
        xr.open_dataset(inputs[1], engine="netcdf4") as accum,
        xr.open_dataset(inputs[2], engine="netcdf4") as mask_file,
    ):
        forcing = prepare_forcing(instant, accum, mask_file["california_mask"])

    columns = ["pv_ac_capacity_factor", "ghi_reference_proxy",
               "poa_global_w_m2", "cell_temperature_c"]
    totals = np.zeros((len(forcing["interval_end"]), len(columns)))
    residual_count, residual_energy, all_energy = 0, 0.0, 0.0
    cell_count = len(forcing["weights"])
    for cell, weight in enumerate(forcing["weights"]):
        ghi = forcing["ghi"][:, cell]
        modeled = model_cell(
            forcing["interval_end"], ghi, forcing["temp_air"][:, cell],
            forcing["latitude"][cell], forcing["longitude"][cell], config,
        )
        totals += modeled[columns].to_numpy() * weight
        residual = (modeled["solar_zenith_deg"].to_numpy() >= 90) & (ghi > 0)
        residual_count += int(residual.sum())
        residual_energy += float(ghi[residual].sum() * weight)
        all_energy += float(ghi.sum() * weight)
        if (cell + 1) % 100 == 0 or cell + 1 == cell_count:
            print(f"Modeled grid cells: {cell + 1}/{cell_count}", flush=True)

    average = pd.DataFrame(totals, index=forcing["interval_end"], columns=columns)
    if not average["pv_ac_capacity_factor"].between(0, 1).all():
        raise ValueError("Area-average AC capacity factor is outside [0, 1].")
    processed = project / "data/processed"
    tables, figures = project / "results/tables", project / "results/figures"
    for directory in [processed, tables, figures]:
        directory.mkdir(parents=True, exist_ok=True)
    csv_path = processed / f"pv_ac_capacity_factor_{args.tag}.csv"
    average.to_csv(csv_path, index_label="interval_end_utc")
    summary = {
        "hourly_intervals": len(average), "selected_grid_centers": cell_count,
        "mean_pv_ac_capacity_factor": float(average["pv_ac_capacity_factor"].mean()),
        "minimum_pv_ac_capacity_factor": float(average["pv_ac_capacity_factor"].min()),
        "maximum_pv_ac_capacity_factor": float(average["pv_ac_capacity_factor"].max()),
        "mean_ghi_reference_proxy": float(average["ghi_reference_proxy"].mean()),
        "missing_values": int(average.isna().sum().sum()),
        "midpoint_below_horizon_positive_ghi_cell_intervals": residual_count,
        "midpoint_below_horizon_share_of_weighted_ghi_energy": (
            residual_energy / all_energy if all_energy else 0.0
        ),
    }
    metadata = {
        "model": "Fixed-tilt, Erbs + isotropic POA + Ross + PVWatts DC/AC",
        "status": "Representative scenario, not calibrated to the California fleet",
        "config": asdict(config), "summary": summary,
        "capacity_factor_denominator": "Rated inverter AC power; 1 W per modeled system",
        "time_convention": "Preceding-hour means, indexed by UTC interval end",
        "solar_geometry": "Interval midpoint; true solar zenith; sea-level pressure/altitude",
        "temperature_timing": "Mean of bracketing t2m snapshots; first interval excluded",
        "first_interval_end_utc": str(average.index[0]),
        "last_interval_end_utc": str(average.index[-1]),
        "spatial_weights": "Cos(latitude), equal AC capacity per unit area in administrative mask",
        "low_sun_rule": "At midpoint zenith >= 87 degrees, use DNI=0 and DHI=GHI",
        "tiny_negative_accumulations_clipped": forcing["tiny_negative_accumulations_clipped"],
        "inputs": [{"path": str(p.relative_to(project)), "sha256": sha256(p)} for p in inputs],
        "python": platform.python_version(),
        "packages": {p: version(p) for p in ["numpy", "pandas", "xarray", "netCDF4", "pvlib"]},
    }
    (tables / f"pv_model_metadata_{args.tag}.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    pd.DataFrame([summary]).to_csv(tables / f"pv_model_summary_{args.tag}.csv", index=False)

    if args.headless:
        import matplotlib
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 1, figsize=(12, 7))
    axes[0].plot(average.index, average["ghi_reference_proxy"],
                 color="tab:orange", label="GHI / 1000 (irradiance reference)", alpha=0.7)
    axes[0].plot(average.index, average["pv_ac_capacity_factor"],
                 color="tab:blue", label="Modeled PV AC capacity factor", linewidth=0.9)
    axes[0].set(xlabel="Interval end (UTC)", ylabel="Normalized value",
                title="January 2020 — representative fixed-tilt PV scenario")
    axes[0].legend()
    axes[1].scatter(average["ghi_reference_proxy"], average["pv_ac_capacity_factor"],
                    s=8, alpha=0.4)
    axes[1].plot([0, 1], [0, 1], "--", color="gray", linewidth=0.8)
    axes[1].set(xlabel="GHI / 1000 (irradiance reference)",
                ylabel="Modeled PV AC capacity factor", xlim=(0, 1), ylim=(0, 1))
    for ax in axes:
        ax.grid(alpha=0.2)
    fig.tight_layout()
    figure_path = figures / f"pv_ac_capacity_factor_{args.tag}.png"
    fig.savefig(figure_path, dpi=200, bbox_inches="tight")
    print(json.dumps(summary, indent=2))
    print("CSV saved to:", csv_path)
    print("Figure saved to:", figure_path)
    if not args.headless:
        plt.show()
    plt.close(fig)


if __name__ == "__main__":
    main()
