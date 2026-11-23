"""Compare modeled temporal shapes with CAISO, without claiming fleet CF accuracy."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from observed_generation import complete_local_days, shape_metrics


def read_hourly(path):
    data = pd.read_csv(path, index_col=0)
    data.index = pd.to_datetime(data.index, utc=True)
    if (data.empty or data.index.has_duplicates or not data.index.is_monotonic_increasing
            or not ((data.index[1:] - data.index[:-1]) == pd.Timedelta(hours=1)).all()
            or not np.isfinite(data.to_numpy(dtype=float)).all()):
        raise ValueError(f"Invalid hourly series: {path.name}")
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--headless", action="store_true")
    args = parser.parse_args()
    project = args.project_dir.resolve()
    processed, tables, figures = project / "data/processed", project / "results/tables", project / "results/figures"
    tables.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)
    names = ["wind_assessment_2020_01.csv", "pv_ac_capacity_factor_2020_01.csv", "caiso_generation_hourly_2020_01.csv"]
    paths = [processed / name for name in names]
    wind, pv, observed = [read_hourly(path) for path in paths]
    if not wind.index.equals(pv.index):
        raise ValueError("Wind/PV intervals must agree exactly before joining observations.")
    metadata_path = tables / "generation_observation_metadata_2020_01.json"
    source_metadata = json.loads(metadata_path.read_text())
    for path, expected in source_metadata["artifacts_sha256"].items():
        if hashlib.sha256((project / path).read_bytes()).hexdigest() != expected:
            raise ValueError(f"Observation checksum mismatch: {path}")
    common = wind.index.intersection(observed.index)
    if len(common) < 48 or not ((common[1:] - common[:-1]) == pd.Timedelta(hours=1)).all():
        raise ValueError("Need at least 48 consecutive aligned observed/model intervals.")
    comparison = pd.concat([wind.loc[common], pv.loc[common, ["pv_ac_capacity_factor"]], observed.loc[common]], axis=1)
    comparison_path = processed / "observed_shape_comparison_2020_01.csv"
    comparison.to_csv(comparison_path, index_label="interval_end_utc")
    daily = complete_local_days(comparison)
    if len(daily) < 3:
        raise ValueError("Need at least three complete days for daily shape diagnostics.")
    daily_path = tables / "observed_shape_daily_means_2020_01.csv"
    daily.to_csv(daily_path, index_label="local_day_start")
    rows = []
    for scenario in [*wind.columns, "pv_ac_capacity_factor"]:
        fuel = "solar" if scenario == "pv_ac_capacity_factor" else "wind"
        obs = f"{fuel}_production_mw"
        row = {"scenario": scenario, "fuel": fuel, **shape_metrics(comparison[scenario], comparison[obs])}
        daily_metrics = shape_metrics(daily[scenario], daily[obs])
        row.update({"complete_local_days": len(daily), "daily_mean_pearson_r": daily_metrics["pearson_r"],
                    "daily_own_mean_scaled_rmse": daily_metrics["own_mean_scaled_rmse"]})
        if fuel == "solar":
            daylight = comparison.pv_ac_capacity_factor > 0
            row["modeled_daylight_hours"] = int(daylight.sum())
            row["modeled_daylight_pearson_r"] = float(np.corrcoef(comparison.loc[daylight, scenario], comparison.loc[daylight, obs])[0, 1])
        rows.append(row)
    metrics_path = tables / "observed_shape_metrics_2020_01.csv"
    pd.DataFrame(rows).to_csv(metrics_path, index=False)
    metadata = {
        "status": "Exploratory temporal-shape comparison across unmatched fleets; not CF/amplitude or event validation",
        "paired_hours": len(common), "complete_local_days": len(daily),
        "first_interval_end_utc": str(common[0]), "last_interval_end_utc": str(common[-1]),
        "model_hours_outside_observation_month": len(wind.index.difference(observed.index)),
        "observation_month_hours_without_model": len(observed.index.difference(wind.index)),
        "source_time_assumption": source_metadata["caiso_time_assumption"],
        "amplitude_handling": "Normalize each series by its own mean over the same paired support; no capacity denominator, fitted gain, lag optimization or bias correction",
        "hourly_rmse_units": "Dimensionless after own-mean scaling; not capacity-factor RMSE",
        "solar_checks": "Hourly correlation includes daily cycle; daylight subset uses modeled PV>0, daily means use complete local days only. No weather-skill claim from hourly correlation alone.",
        "curtailment": "Reported separately; production only used as observation. Neither reconstructed potential nor low-resource events inferred.",
        "scope_limits": ["CAISO balancing area is not the California administrative mask or EIA fixed reference fleet",
                         "CAISO Solar technology mix is not assumed to be PV-only; model is fixed-tilt PV",
                         "Wind/solar net production includes operational effects absent from reference resource models",
                         "One month and autocorrelated hours/days provide no independent out-of-sample validation"],
        "input_sha256": {str(path.relative_to(project)): hashlib.sha256(path.read_bytes()).hexdigest()
                         for path in [*paths, metadata_path]},
    }
    if args.headless:
        import matplotlib
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    fig, axes = plt.subplots(2, 2, figsize=(14, 8))
    wind_series = ["cubic_uniform", "wtk_iec2_eia2020"]
    for ax, fuel, scenarios in [(axes[0, 0], "wind", wind_series), (axes[0, 1], "solar", ["pv_ac_capacity_factor"])]:
        obs = f"{fuel}_production_mw"
        ax.plot(common, comparison[obs] / comparison[obs].mean(), color="black", linewidth=1, label="CAISO production")
        for scenario in scenarios:
            ax.plot(common, comparison[scenario] / comparison[scenario].mean(), linewidth=.8, alpha=.8, label=scenario)
        ax.set(title=f"Hourly {fuel}: each series divided by its own paired mean", ylabel="Relative output", xlabel="Interval end (UTC)")
        locator = mdates.AutoDateLocator(minticks=3, maxticks=5)
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
        ax.legend(fontsize=8)
    for ax, fuel, scenario in [(axes[1, 0], "wind", "wtk_iec2_eia2020"), (axes[1, 1], "solar", "pv_ac_capacity_factor")]:
        obs = f"{fuel}_production_mw"
        x, y = daily[obs] / daily[obs].mean(), daily[scenario] / daily[scenario].mean()
        ax.scatter(x, y, s=24)
        limit = max(x.max(), y.max()) * 1.05
        ax.plot([0, limit], [0, limit], "--", color="gray", linewidth=.7)
        ax.set(title=f"{len(daily)} complete Pacific days — {fuel}", xlabel="CAISO daily mean / its mean", ylabel="Modeled daily mean / its mean")
    for ax in axes.ravel():
        ax.grid(alpha=.2)
    fig.suptitle("January 2020 — preliminary comparison of temporal shapes across unmatched fleets", fontsize=13)
    fig.tight_layout()
    figure_path = figures / "observed_generation_shapes_2020_01.png"
    fig.savefig(figure_path, dpi=180)
    plt.close(fig)
    metadata["artifacts_sha256"] = {str(path.relative_to(project)): hashlib.sha256(path.read_bytes()).hexdigest()
                                     for path in [comparison_path, daily_path, metrics_path, figure_path]}
    (tables / "observed_shape_comparison_metadata_2020_01.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(pd.DataFrame(rows).to_string(index=False))
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
