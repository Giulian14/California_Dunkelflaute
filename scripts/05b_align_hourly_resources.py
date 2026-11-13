#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Nov 12 19:45:33 2026

@author: giulianlaudisa
"""

"""Align preliminary wind and solar estimates to hourly intervals.

Approximate preceding-hour wind CF using adjacent snapshot averages.
Solar already represents the preceding hour.
"""

from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parent.parent


def main():
    processed_dir = PROJECT_DIR / "data" / "processed"

    wind = pd.read_csv(
        processed_dir / "illustrative_wind_cf_2020_01.csv",
        index_col="time_utc",
        parse_dates=True,
    )
    solar = pd.read_csv(
        processed_dir / "solar_resource_proxy_2020_01.csv",
        index_col="time_utc",
        parse_dates=True,
    )

    expected = pd.date_range("2020-01-01", periods=744, freq="h")

    for name, table in [("Wind", wind), ("Solar", solar)]:
        if not table.index.equals(expected):
            raise ValueError(f"{name}: unexpected hourly timestamps.")
        if not np.isfinite(table.to_numpy()).all():
            raise ValueError(f"{name}: missing or infinite values.")

    hourly = pd.DataFrame(index=expected)
    hourly["wind_cf_hourly_approx"] = (
        wind["wind_capacity_factor"].rolling(2).mean()
    )
    hourly["solar_resource_proxy"] = solar["solar_resource_proxy"]

    # First interval lacks the preceding wind snapshot.
    hourly = hourly.iloc[1:].copy()

    output_path = (
        processed_dir / "preliminary_hourly_resources_2020_01.csv"
    )
    hourly.to_csv(output_path, index_label="interval_end_utc")

    print("Hourly intervals:", len(hourly))
    print("First interval ends:", hourly.index[0])
    print("Last interval ends:", hourly.index[-1])
    print("Saved to:", output_path)


if __name__ == "__main__":
    main()