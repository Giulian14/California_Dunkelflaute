#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Nov 12 19:35:53 2026

@author: giulianlaudisa
"""

"""Calculate a preliminary solar resource proxy for January 2020.

Proxy = preceding-hour mean irradiance / 1,000 W/m², clipped to 0–1.
Uses area weighting within California's administrative boundary.
This is not a full photovoltaic generation model.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import xarray as xr


PROJECT_DIR = Path(__file__).resolve().parent.parent


def main():
    raw_dir = PROJECT_DIR / "data" / "raw"
    processed_dir = PROJECT_DIR / "data" / "processed"
    figure_dir = PROJECT_DIR / "results" / "figures"

    processed_dir.mkdir(parents=True, exist_ok=True)
    figure_dir.mkdir(parents=True, exist_ok=True)

    with (
        xr.open_dataset(
            raw_dir / "data_stream-oper_stepType-accum.nc",
            engine="netcdf4",
        ) as accum,
        xr.open_dataset(
            processed_dir / "california_mask.nc",
            engine="netcdf4",
        ) as mask_file,
    ):
        accum, mask = xr.align(
            accum,
            mask_file["california_mask"].astype(bool),
            join="exact",
        )

        # Hourly CDS ERA5: J/m² to preceding-hour mean W/m².
        irradiance = accum["ssrd"] / 3600.0
        proxy_grid = (irradiance / 1000.0).clip(min=0, max=1)

        weights = np.cos(np.deg2rad(accum["latitude"]))
        average = (
            proxy_grid.where(mask)
            .weighted(weights)
            .mean(dim=["latitude", "longitude"])
            .load()
        )

    average.name = "solar_resource_proxy"
    csv_path = processed_dir / "solar_resource_proxy_2020_01.csv"
    average.to_series().to_csv(csv_path, index_label="time_utc")

    print("Hourly records:", average.sizes["valid_time"])
    print("Missing hours:", int(average.isnull().sum().item()))
    print(f"Monthly mean: {average.mean().item():.3f}")
    print(f"Minimum: {average.min().item():.3f}")
    print(f"Maximum: {average.max().item():.3f}")

    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(average["valid_time"], average, color="tab:orange")
    ax.set_title("January 2020 — California solar resource proxy")
    ax.set_xlabel("Time (UTC)")
    ax.set_ylabel("Solar resource proxy (0–1)")
    ax.set_ylim(0, 1)
    ax.grid(alpha=0.3)
    fig.tight_layout()

    figure_path = figure_dir / "solar_resource_proxy_2020_01.png"
    fig.savefig(figure_path, dpi=300, bbox_inches="tight")

    print("CSV saved to:", csv_path)
    print("Figure saved to:", figure_path)
    plt.show()


if __name__ == "__main__":
    main()