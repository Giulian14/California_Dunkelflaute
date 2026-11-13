#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Nov 12 19:33:28 2026

@author: giulianlaudisa
"""

"""Illustrative wind capacity factors for January 2020.

Assumes uniformly distributed capacity within California's administrative
boundary. This is not a model of the actual California wind fleet.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import xarray as xr


PROJECT_DIR = Path(__file__).resolve().parent.parent


def wind_capacity_factor(speed):
    """Illustrative cubic curve: cut-in 3, rated 12, cut-out 25 m/s."""
    cf = xr.where(
        (speed >= 3.0) & (speed < 12.0),
        (speed**3 - 3.0**3) / (12.0**3 - 3.0**3),
        xr.where((speed >= 12.0) & (speed < 25.0), 1.0, 0.0),
    )
    return cf.where(np.isfinite(speed))


def main():
    raw_dir = PROJECT_DIR / "data" / "raw"
    processed_dir = PROJECT_DIR / "data" / "processed"
    figure_dir = PROJECT_DIR / "results" / "figures"
    processed_dir.mkdir(parents=True, exist_ok=True)
    figure_dir.mkdir(parents=True, exist_ok=True)

    with (
        xr.open_dataset(
            raw_dir / "data_stream-oper_stepType-instant.nc",
            engine="netcdf4",
        ) as instant,
        xr.open_dataset(
            processed_dir / "california_mask.nc",
            engine="netcdf4",
        ) as mask_file,
    ):
        instant, mask = xr.align(
            instant,
            mask_file["california_mask"].astype(bool),
            join="exact",
        )

        speed = np.hypot(instant["u100"], instant["v100"])
        cf_grid = wind_capacity_factor(speed)
        weights = np.cos(np.deg2rad(instant["latitude"]))

        average = (
            cf_grid.where(mask)
            .weighted(weights)
            .mean(dim=["latitude", "longitude"])
            .load()
        )

    average.name = "wind_capacity_factor"
    csv_path = processed_dir / "illustrative_wind_cf_2020_01.csv"
    average.to_series().to_csv(csv_path, index_label="time_utc")

    print("Hourly records:", average.sizes["valid_time"])
    print("Missing hours:", int(average.isnull().sum().item()))
    print(f"Monthly mean: {average.mean().item():.3f}")
    print(f"Minimum: {average.min().item():.3f}")
    print(f"Maximum: {average.max().item():.3f}")

    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(average["valid_time"], average)
    ax.set_title(
        "January 2020 — illustrative California wind capacity factor"
    )
    ax.set_xlabel("Time (UTC)")
    ax.set_ylabel("Capacity factor")
    ax.set_ylim(0, 1)
    ax.grid(alpha=0.3)
    fig.tight_layout()

    figure_path = figure_dir / "illustrative_wind_cf_2020_01.png"
    fig.savefig(figure_path, dpi=300, bbox_inches="tight")
    print("CSV saved to:", csv_path)
    print("Figure saved to:", figure_path)
    plt.show()


if __name__ == "__main__":
    main()