#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Nov 12 14:44:38 2026

@author: giulianlaudisa
"""

"""Calculate area-weighted weather averages within the California mask."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import xarray as xr


PROJECT_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_DIR / "data" / "raw"
PROCESSED_DIR = PROJECT_DIR / "data" / "processed"
FIGURE_DIR = PROJECT_DIR / "results" / "figures"


def main():
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)

    with (
        xr.open_dataset(
            RAW_DIR / "data_stream-oper_stepType-instant.nc",
            engine="netcdf4",
        ) as instant,
        xr.open_dataset(
            RAW_DIR / "data_stream-oper_stepType-accum.nc",
            engine="netcdf4",
        ) as accum,
        xr.open_dataset(
            PROCESSED_DIR / "california_mask.nc",
            engine="netcdf4",
        ) as mask_file,
    ):
        mask = mask_file["california_mask"].astype(bool)
        instant, accum, mask = xr.align(
            instant, accum, mask, join="exact"
        )

        fields = xr.Dataset({
            "wind_speed": np.hypot(instant["u100"], instant["v100"]),
            "temperature_c": instant["t2m"] - 273.15,
            # Hourly CDS ERA5 accumulation: J/m² to mean W/m².
            "irradiance": accum["ssrd"] / 3600.0,
        })

        weights = np.cos(np.deg2rad(fields["latitude"]))
        averages = (
            fields.where(mask)
            .weighted(weights)
            .mean(dim=["latitude", "longitude"])
            .load()
        )

    csv_path = PROCESSED_DIR / "california_hourly_weather_2020_01.csv"
    averages.to_dataframe()[
        ["wind_speed", "temperature_c", "irradiance"]
    ].to_csv(csv_path, index_label="time_utc")

    panels = [
        ("wind_speed", "100 m wind (m/s)", "tab:blue"),
        ("temperature_c", "Temperature (°C)", "tab:red"),
        ("irradiance", "Irradiance (W/m²)", "tab:orange"),
    ]
    fig, axes = plt.subplots(3, 1, figsize=(12, 8), sharex=True)

    for ax, (name, label, color) in zip(axes, panels):
        ax.plot(averages["valid_time"], averages[name], color=color)
        ax.set_ylabel(label)
        ax.grid(alpha=0.3)

    axes[0].set_title(
        "January 2020 — California administrative-area averages"
    )
    axes[-1].set_xlabel("Time (UTC)")
    fig.tight_layout()

    figure_path = FIGURE_DIR / "era5_california_january_2020.png"
    fig.savefig(figure_path, dpi=300, bbox_inches="tight")

    print("Rows saved:", averages.sizes["valid_time"])
    print("CSV saved to:", csv_path)
    print("Figure saved to:", figure_path)
    plt.show()


if __name__ == "__main__":
    main()