"""Compare original proxy, modeled-PV hourly events and 48-hour combined energy."""

import argparse
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import platform
import re

import numpy as np
import pandas as pd

from energy_events import (
    align_wind_pv, combined_window_events, read_series, simultaneous_events,
)

WIND_SHARES = (0.25, 0.50, 0.75)
COMBINED_THRESHOLDS = (0.05, 0.06, 0.10)
DURATIONS = (6, 12, 18, 24, 48)


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
    processed, tables, figures = [project / p for p in
                                  ["data/processed", "results/tables", "results/figures"]]
    for directory in [processed, tables, figures]:
        directory.mkdir(parents=True, exist_ok=True)
    wind_path = processed / f"illustrative_wind_cf_{args.tag}.csv"
    wind = read_series(wind_path, "wind_capacity_factor")
    proxy_path = processed / f"solar_resource_proxy_{args.tag}.csv"
    proxy = read_series(proxy_path, "solar_resource_proxy")
    if not proxy.index.equals(wind.index):
        raise ValueError("Original proxy timestamps must match wind snapshots.")
    inputs = [wind_path, proxy_path]
    scenarios = {"original_proxy": align_wind_pv(wind, proxy.iloc[1:])}
    pv_metadata = {}
    for label, suffix in [("tilt25", "_tilt25"), ("baseline", ""), ("tilt45", "_tilt45")]:
        path = processed / f"pv_ac_capacity_factor_{args.tag}{suffix}.csv"
        scenarios[label] = align_wind_pv(wind, read_series(path, "pv_ac_capacity_factor"))
        inputs.append(path)
        metadata_path = tables / f"pv_model_metadata_{args.tag}{suffix}.json"
        pv_metadata[label] = json.loads(metadata_path.read_text(encoding="utf-8"))
        inputs.append(metadata_path)
    for label, expected_tilt in [("tilt25", 25), ("baseline", 35), ("tilt45", 45)]:
        config = pv_metadata[label]["config"].copy()
        if config.pop("tilt_deg") != expected_tilt:
            raise ValueError(f"{label}: PV metadata does not match the specified tilt.")
        baseline_config = pv_metadata["baseline"]["config"].copy()
        baseline_config.pop("tilt_deg")
        if config != baseline_config or pv_metadata[label]["inputs"] != pv_metadata["baseline"]["inputs"]:
            raise ValueError("PV scenarios must share other assumptions and raw inputs.")
    if len(scenarios["baseline"]) < 48:
        raise ValueError("The comparison needs at least 48 complete hourly intervals.")

    reference_rows, duration_rows, reference_catalogues = [], [], []
    for label, resources in scenarios.items():
        low, periods = simultaneous_events(resources)
        eligible = periods.loc[periods.meets_minimum_duration]
        reference_rows.append({
            "solar_scenario": label, "threshold_each_technology": 0.20,
            "minimum_event_hours": 24, "input_intervals": len(resources),
            "simultaneous_low_hours": int(low.sum()), "observed_low_periods": len(periods),
            "longest_observed_period_hours": int(periods.duration_hours.max()) if len(periods) else 0,
            "events_at_least_24_hours": len(eligible),
            "complete_events_at_least_24_hours": int((~eligible.boundary_context_incomplete).sum()),
            "boundary_touching_low_periods": int(periods.boundary_context_incomplete.sum()),
        })
        for hours in DURATIONS:
            subset = periods.loc[periods.duration_hours >= hours]
            duration_rows.append({"solar_scenario": label, "minimum_duration_hours": hours,
                                  "all_observed_periods": len(subset),
                                  "complete_periods": int((~subset.boundary_context_incomplete).sum())})
        reference_catalogues.append(periods.assign(solar_scenario=label))

    sensitivity_rows, combined_catalogues = [], []
    baseline_diagnostic, baseline_resources = None, scenarios["baseline"]
    for label, resources in scenarios.items():
        if label == "original_proxy":
            continue
        for share in WIND_SHARES:
            for threshold in COMBINED_THRESHOLDS:
                diagnostic, events = combined_window_events(resources, share, threshold)
                sensitivity_rows.append({
                    "solar_scenario": label, "wind_rated_capacity_share": share,
                    "combined_cf_threshold": threshold, "window_hours": 48,
                    "input_intervals": len(resources),
                    "complete_windows_available": int(diagnostic.full_window_available.sum()),
                    "minimum_48h_combined_cf": float(diagnostic.rolling_mean_cf.min()),
                    "qualifying_windows": int(diagnostic.qualifying_window_endpoint.sum()),
                    "covered_hours": int(diagnostic.covered_by_qualifying_window.sum()),
                    "observed_merged_events": len(events),
                    "complete_merged_events": int((~events.boundary_context_incomplete).sum()),
                    "edge_context_uncertain_events": int(events.boundary_context_incomplete.sum()),
                    "longest_observed_event_hours": int(events.duration_hours.max()) if len(events) else 0,
                })
                combined_catalogues.append(events.assign(
                    solar_scenario=label, wind_rated_capacity_share=share,
                    combined_cf_threshold=threshold, window_hours=48,
                ))
                if label == "baseline" and share == 0.50 and threshold == 0.06:
                    baseline_diagnostic = diagnostic

    reference = pd.DataFrame(reference_rows)
    sensitivity = pd.DataFrame(sensitivity_rows)
    reference.to_csv(tables / f"pv_reference_summary_{args.tag}.csv", index=False)
    pd.DataFrame(duration_rows).to_csv(
        tables / f"pv_reference_duration_sensitivity_{args.tag}.csv", index=False)
    pd.concat(reference_catalogues, ignore_index=True).to_csv(
        tables / f"pv_reference_periods_{args.tag}.csv", index=False)
    sensitivity.to_csv(tables / f"wind_pv_48h_sensitivity_{args.tag}.csv", index=False)
    pd.concat(combined_catalogues, ignore_index=True).to_csv(
        tables / f"wind_pv_48h_events_{args.tag}.csv", index=False)
    baseline_series = baseline_resources.join(baseline_diagnostic)
    baseline_series["original_ghi_proxy"] = scenarios["original_proxy"].pv_cf
    baseline_series.to_csv(processed / f"wind_pv_event_inputs_{args.tag}.csv",
                            index_label="interval_end_utc")
    metadata = {
        "status": "January scenario comparison; not a long-term climatology or actual fleet adequacy study",
        "reference": {"threshold_each_cf": 0.20, "minimum_hours": 24},
        "combined": {"window_hours": 48, "wind_rated_capacity_shares": WIND_SHARES,
                     "thresholds": COMBINED_THRESHOLDS, "baseline_wind_share": 0.50,
                     "baseline_threshold": 0.06},
        "duration_rule": "Union of all complete qualifying window supports; merge overlap and adjacency",
        "edge_context_rule": "Conservatively flag events within 48 hours of either data boundary",
        "time_rule": "UTC interval ends; only wind snapshots averaged; PV not smoothed again",
        "first_interval_start_utc": str(baseline_series.index[0] - pd.Timedelta(hours=1)),
        "last_interval_end_utc": str(baseline_series.index[-1]),
        "expected_unavailable_initial_rolling_means": 47,
        "inputs": [{"path": str(p.relative_to(project)),
                    "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in inputs],
        "python": platform.python_version(),
        "packages": {p: version(p) for p in ["numpy", "pandas", "matplotlib"]},
    }
    (tables / f"event_comparison_metadata_{args.tag}.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8")

    if args.headless:
        import matplotlib
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(3, 1, figsize=(12, 11))
    for column, label in [("wind_cf", "Illustrative wind CF"), ("pv_cf", "Modeled PV AC CF")]:
        axes[0].plot(baseline_series.index, baseline_series[column], label=label, linewidth=0.8)
    axes[0].axhline(0.20, color="gray", linestyle="--", label="Hourly threshold for each")
    axes[0].set(title="January 2020 — reference and 48-hour energy comparison",
                ylabel="Capacity factor", xlabel="Interval end (UTC)")
    axes[0].legend()
    for share in WIND_SHARES:
        diagnostic, _ = combined_window_events(baseline_resources, share)
        axes[1].plot(diagnostic.index, diagnostic.rolling_mean_cf,
                     label=f"Wind rated capacity share: {share:.0%}")
    axes[1].axhline(0.06, color="black", linestyle="--", label="Literature-comparison threshold: 0.06")
    axes[1].axvspan(
        baseline_series.index[0] - pd.Timedelta(hours=1), baseline_series.index[47],
        color="gray", alpha=0.12, label="Initial incomplete rolling context",
    )
    axes[1].set_xlim(axes[0].get_xlim())
    axes[1].set(ylabel="48-hour mean combined CF", xlabel="Window end (UTC)")
    axes[1].legend(fontsize=8)
    for ax in axes[:2]:
        ax.grid(alpha=0.2)
    base = sensitivity.loc[sensitivity.solar_scenario == "baseline"]
    matrix = base.pivot(index="combined_cf_threshold", columns="wind_rated_capacity_share",
                         values="covered_hours").reindex(index=COMBINED_THRESHOLDS, columns=WIND_SHARES)
    heat = axes[2].imshow(matrix, aspect="auto", vmin=0, vmax=len(baseline_resources), cmap="viridis")
    for row, threshold in enumerate(COMBINED_THRESHOLDS):
        for col, share in enumerate(WIND_SHARES):
            result = base.loc[(base.combined_cf_threshold == threshold)
                              & (base.wind_rated_capacity_share == share)].iloc[0]
            count = int(result.observed_merged_events)
            word = "event" if count == 1 else "events"
            text = f"{count} {word}; {int(result.covered_hours)} h"
            if result.edge_context_uncertain_events:
                text += " *"
            axes[2].text(col, row, text, ha="center", va="center", color="white" if result.covered_hours < 400 else "black")
    axes[2].set(xticks=range(3), xticklabels=["25%", "50%", "75%"],
                yticks=range(3), yticklabels=["0.05", "0.06", "0.10"],
                xlabel="Wind share of rated wind + PV capacity", ylabel="Combined CF threshold",
                title="35° PV scenario: observed union events (* includes uncertain edge context)")
    fig.colorbar(heat, ax=axes[2], label="Hours covered by qualifying windows")
    fig.tight_layout()
    fig.savefig(figures / f"wind_pv_event_comparison_{args.tag}.png", dpi=200, bbox_inches="tight")
    if not args.headless:
        plt.show()
    plt.close(fig)
    print("Reference comparison:")
    print(reference.to_string(index=False))
    print("\n48-hour sensitivity for 35° PV:")
    print(base.to_string(index=False))


if __name__ == "__main__":
    main()
