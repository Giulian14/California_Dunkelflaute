"""Audit CAISO, EIA-930 and EIA-923 totals without forcing a reconciliation."""

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from january_wind import eia930_january


def checksum(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--eia930-response", type=Path, required=True)
    parser.add_argument("--eia930-route-metadata", type=Path, required=True)
    parser.add_argument("--retrieved-on", required=True)
    parser.add_argument("--project-dir", type=Path, default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args()
    date.fromisoformat(args.retrieved_on)
    project = args.project_dir.resolve()
    processed, tables = project / "data/processed", project / "results/tables"
    source = json.loads(args.eia930_response.read_text())
    route = json.loads(args.eia930_route_metadata.read_text())
    frequencies = route["response"]["frequency"]
    if not any(item["id"] == "hourly" and "UTC" in item["description"] for item in frequencies):
        raise ValueError("Route metadata must explicitly identify hourly frequency as UTC.")
    eia = eia930_january(source)
    caiso_path = processed / "caiso_generation_hourly_2020_01.csv"
    caiso_meta_path = tables / "generation_observation_metadata_2020_01.json"
    caiso_meta = json.loads(caiso_meta_path.read_text())
    if checksum(caiso_path) != caiso_meta["artifacts_sha256"][str(caiso_path.relative_to(project))]:
        raise ValueError("CAISO extraction checksum mismatch.")
    caiso = pd.read_csv(caiso_path, index_col=0)
    caiso.index = pd.to_datetime(caiso.index, utc=True)
    if not caiso.index.equals(eia.index):
        raise ValueError("CAISO and EIA-930 interval-end support disagree.")
    paired = pd.concat([eia, caiso[["wind_production_mw", "solar_production_mw"]]], axis=1)
    paired_path = processed / "generation_source_hourly_audit_2020_01.csv"
    paired.to_csv(paired_path, index_label="interval_end_utc")
    rows, metrics = [], []
    for fuel in ["wind", "solar"]:
        a, b = paired[f"eia930_{fuel}_mwh"], paired[f"{fuel}_production_mw"]
        metrics.append({"fuel": fuel, "paired_hours": len(paired), "eia930_energy_mwh": a.sum(),
            "caiso_energy_mwh": b.sum(), "eia930_minus_caiso_mwh": (a-b).sum(),
            "difference_fraction_of_caiso_energy": (a.sum()-b.sum()) / b.sum(),
            "hourly_pearson_r": a.corr(b), "hourly_rmse_mwh": float(np.sqrt(np.mean((a-b)**2))),
            "negative_eia930_hours": int(a.lt(0).sum()), "negative_caiso_hours": int(b.lt(0).sum())})
        for label, energy in [("EIA-930 CISO", a.sum()), ("CAISO raw archive", b.sum())]:
            rows.append({"source_scope": label, "technology": fuel, "january_energy_mwh": energy,
                         "missing_source_rows": 0})
    eia_summary_path = tables / "eia923_generation_scope_summary_2020_01.csv"
    if checksum(eia_summary_path) != caiso_meta["artifacts_sha256"][str(eia_summary_path.relative_to(project))]:
        raise ValueError("EIA-923 scope summary checksum mismatch.")
    for row in pd.read_csv(eia_summary_path).itertuples():
        rows.append({"source_scope": f"EIA-923 {row.scope}",
            "technology": {"WT": "wind", "PV": "solar PV", "ST": "solar thermal"}[row.prime_mover],
            "january_energy_mwh": row.available_january_generation_mwh, "missing_source_rows": row.missing_january_rows})
    summary_path = tables / "generation_source_monthly_audit_2020_01.csv"
    pd.DataFrame(rows).to_csv(summary_path, index=False)
    metrics_path = tables / "generation_source_hourly_metrics_2020_01.csv"
    pd.DataFrame(metrics).to_csv(metrics_path, index=False)
    metadata = {
        "retrieved_on": args.retrieved_on,
        "EIA930_endpoint": "https://api.eia.gov/v2/electricity/rto/fuel-type-data/data/",
        "query_without_credentials": {"frequency": "hourly", "data": ["value"], "respondent": ["CISO"],
            "fueltype": ["WND", "SUN"], "start": "2020-01-01T09", "end": "2020-02-01T08", "length": 5000},
        "raw_response_sha256": checksum(args.eia930_response),
        "route_metadata_endpoint": "https://api.eia.gov/v2/electricity/rto/fuel-type-data/",
        "route_metadata_sha256": checksum(args.eia930_route_metadata),
        "time_convention": "Route identifies hourly as UTC; EIA-930 documentation specifies hourly interval-end labels",
        "negative_values": "Preserved as reported net energy, never clipped to force agreement",
        "monthly_resolution": "EIA-923 plant-level and EIA-930 BA-level populations remain unreconciled; no correction factor applied",
        "reporting_frequency_clarification": "Annual submission frequency is not annual-only generation: EIA-923 Schedule 3D requires wind/solar annual respondents to supply each month's operations. It alone does not imply estimated monthly allocation.",
        "interpretation": "EIA-930 and CAISO are BA operational series, not independent plant-matched validation targets; close agreement does not resolve their difference from EIA-923",
        "input_sha256": {str(p.relative_to(project)): checksum(p) for p in [caiso_path, caiso_meta_path, eia_summary_path]},
        "artifacts_sha256": {str(p.relative_to(project)): checksum(p) for p in [paired_path, summary_path, metrics_path]},
    }
    (tables / "generation_source_audit_metadata_2020_01.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(pd.DataFrame(metrics).to_string(index=False))


if __name__ == "__main__":
    main()
