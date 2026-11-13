#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Nov 12 19:43:21 2026

@author: giulianlaudisa
"""

"""Detect preliminary low-resource periods, including boundary flags.

Trial thresholds: wind approximation < 0.20 and solar proxy < 0.20.
These are exploratory periods, not validated Dunkelflaute events.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parent.parent
WIND_THRESHOLD = 0.20
SOLAR_THRESHOLD = 0.20


def main():
    processed_dir = PROJECT_DIR / "data" / "processed"
    table_dir = PROJECT_DIR / "results" / "tables"
    figure_dir = PROJECT_DIR / "results" / "figures"
    table_dir.mkdir(parents=True, exist_ok=True)
    figure_dir.mkdir(parents=True, exist_ok=True)

    data = pd.read_csv(
        processed_dir / "preliminary_hourly_resources_2020_01.csv",
        index_col="interval_end_utc",
        parse_dates=True,
    )

    expected = pd.date_range("2020-01-01 01:00", periods=743, freq="h")
    if not data.index.equals(expected):
        raise ValueError("Expected 743 consecutive hourly intervals.")

    columns = ["wind_cf_hourly_approx", "solar_resource_proxy"]
    if not np.isfinite(data[columns].to_numpy()).all():
        raise ValueError("Resource data contain missing or infinite values.")

    low = (
        (data["wind_cf_hourly_approx"] < WIND_THRESHOLD)
        & (data["solar_resource_proxy"] < SOLAR_THRESHOLD)
    )
    groups = low.ne(low.shift()).cumsum()

    flagged = pd.DataFrame({
        "interval_end": data.index,
        "low": low.to_numpy(),
        "group": groups.to_numpy(),
    })

    periods = (
        flagged.loc[flagged["low"]]
        .groupby("group")
        .agg(
            first_interval_end=("interval_end", "min"),
            last_interval_end=("interval_end", "max"),
            duration_hours=("interval_end", "size"),
        )
        .reset_index(drop=True)
    )

    periods["start_utc"] = (
        periods["first_interval_end"] - pd.Timedelta(hours=1)
    )
    periods["end_utc"] = periods["last_interval_end"]
    periods["touches_start"] = (
        periods["first_interval_end"] == data.index[0]
    )
    periods["touches_end"] = (
        periods["last_interval_end"] == data.index[-1]
    )
    periods = periods[
        ["start_utc", "end_utc", "duration_hours",
         "touches_start", "touches_end"]
    ]

    complete = periods.loc[
        ~(periods["touches_start"] | periods["touches_end"])
    ]

    summary = pd.DataFrame({
        "minimum_duration_hours": [6, 12, 18, 24, 48],
    })
    summary["all_observed_periods"] = [
        int((periods["duration_hours"] >= hours).sum())
        for hours in summary["minimum_duration_hours"]
    ]
    summary["fully_observed_periods"] = [
        int((complete["duration_hours"] >= hours).sum())
        for hours in summary["minimum_duration_hours"]
    ]

    periods.to_csv(
        table_dir / "trial_low_resource_periods_2020_01.csv",
        index=False,
    )
    summary.to_csv(
        table_dir / "trial_duration_sensitivity_2020_01.csv",
        index=False,
    )

    print("Low-resource hours:", int(low.sum()))
    print("Total periods:", len(periods))
    print("Fully observed periods:", len(complete))
    print("\nDuration sensitivity:")
    print(summary.to_string(index=False))

    fig, ax = plt.subplots(figsize=(8, 4))
    if not periods.empty:
        durations = periods["duration_hours"]
        bins = np.arange(0.5, durations.max() + 1.5, 1)
        ax.hist(
            durations, bins=bins,
            color="tab:blue", edgecolor="white",
        )

    ax.axvline(
        24, color="tab:red", linestyle="--",
        label="Trial minimum duration: 24 hours",
    )
    ax.set_xlim(0, 26)
    ax.set_xlabel("Consecutive hours with both values below 0.20")
    ax.set_ylabel("Number of uninterrupted periods")
    ax.set_title("January 2020 — preliminary low-resource durations")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.text(
        0.5, 0.01,
        "Includes boundary-touching periods with potentially incomplete durations.",
        ha="center", fontsize=8,
    )
    fig.tight_layout(rect=[0, 0.04, 1, 1])
    fig.savefig(
        figure_dir / "trial_low_resource_duration_histogram_2020_01.png",
        dpi=300, bbox_inches="tight",
    )
    plt.show()


if __name__ == "__main__":
    main()