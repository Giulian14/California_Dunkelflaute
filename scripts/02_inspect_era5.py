#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Nov 11 16:10:06 2026

@author: giulianlaudisa
"""

"""Inspect January 2020 ERA5 files and plot bounding-box averages."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import xarray as xr


# Find the project relative to this script's location in scripts/.
PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "data" / "raw"
FIGURE_DIR = PROJECT_DIR / "results" / "figures"


def main():
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)

    with (
        xr.open_dataset(
            DATA_DIR / "data_stream-oper_stepType-instant.nc",
            engine="netcdf4",
        ) as ds_instant,
        xr.open_dataset(
            DATA_DIR / "data_stream-oper_stepType-accum.nc",
            engine="netcdf4",
        ) as ds_accum,
    ):
        print("INSTANTANEOUS DATA")
        print(ds_instant)
        print("\nACCUMULATED DATA")
        print(ds_accum)

        # Require matching timestamps and spatial coordinates.
        ds_instant, ds_accum = xr.align(
            ds_instant, ds_accum, join="exact"
        )

        expected_time = np.arange(
            np.datetime64("2020-01-01T00", "h"),
            np.datetime64("2020-02-01T00", "h"),
            np.timedelta64(1, "h"),
        )
        if not np.array_equal(
            ds_instant["valid_time"].values, expected_time
        ):
            raise ValueError("Expected all 744 hourly January 2020 timestamps.")

        wind_speed = np.hypot(ds_instant["u100"], ds_instant["v100"])
        temperature_c = ds_instant["t2m"] - 273.15

        # CDS hourly ERA5 single-levels: energy over the preceding hour.
        # Convert J/m² to hourly mean W/m².
        irradiance = ds_accum["ssrd"] / 3600.0

        variables = [
            ("100 m wind (m/s)", wind_speed, "tab:blue"),
            ("Temperature (°C)", temperature_c, "tab:red"),
            ("Irradiance (W/m²)", irradiance, "tab:orange"),
        ]

        # Area weighting for a regular latitude–longitude grid.
        # These averages include the entire box, including ocean.
        weights = np.cos(np.deg2rad(ds_instant["latitude"]))

        fig, axes = plt.subplots(
            3, 1, figsize=(12, 8), sharex=True
        )

        for ax, (label, variable, color) in zip(axes, variables):
            print(f"\n{label}")
            print(f"Minimum: {variable.min().item():.2f}")
            print(f"Maximum: {variable.max().item():.2f}")
            print(f"Missing values: {variable.isnull().sum().item()}")

            average = variable.weighted(weights).mean(
                dim=["latitude", "longitude"]
            )
            ax.plot(average["valid_time"], average, color=color)
            ax.set_ylabel(label)
            ax.grid(alpha=0.3)

        axes[0].set_title(
            "January 2020 — ERA5 bounding-box averages"
        )
        axes[-1].set_xlabel("Time (UTC)")
        fig.tight_layout()

        figure_path = FIGURE_DIR / "era5_bounding_box_january_2020.png"
        fig.savefig(figure_path, dpi=300, bbox_inches="tight")
        print("\nFigure saved to:", figure_path)
        plt.show()


if __name__ == "__main__":
    main()