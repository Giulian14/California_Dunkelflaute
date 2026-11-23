"""Build a conservative whole-plant January wind cohort from official snapshots."""

import argparse
from datetime import date
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import platform

import pandas as pd
from shapely.geometry import shape

from january_wind import match_january_plants, monthly_wind


def checksum(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--december-workbook", required=True, type=Path)
    parser.add_argument("--january-workbook", required=True, type=Path)
    parser.add_argument("--retrieved-on", required=True)
    parser.add_argument("--project-dir", type=Path, default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args()
    date.fromisoformat(args.retrieved_on)
    project = args.project_dir.resolve()
    reference, tables = project / "data/reference", project / "results/tables"
    reference.mkdir(parents=True, exist_ok=True)
    tables.mkdir(parents=True, exist_ok=True)
    sources = [args.december_workbook, args.january_workbook]
    snapshots = []
    for path, month in zip(sources, ["December 2019", "January 2020"]):
        title = pd.read_excel(path, sheet_name="Operating", header=None, nrows=1, engine="openpyxl").iloc[0, 0]
        if title != f"Inventory of Operating Generators as of {month}":
            raise ValueError("Unexpected monthly workbook title/date.")
        snapshots.append(monthly_wind(pd.read_excel(path, sheet_name="Operating", header=1, engine="openpyxl")))
    december, january = snapshots
    retired = pd.read_excel(args.january_workbook, sheet_name="Retired", header=1, engine="openpyxl")
    retired = retired.loc[retired["Plant State"].eq("CA") & retired.Technology.eq("Onshore Wind Turbine")
        & ((retired["Retirement Year"].eq(2020) & retired["Retirement Month"].eq(1))
           | (retired["Retirement Year"].eq(2019) & retired["Retirement Month"].eq(12)))].copy()
    retired["source_excel_row"] = retired.index + 3
    retired = retired.rename(columns={"Plant ID": "plant_id", "Generator ID": "generator_id",
        "Plant Name": "plant_name", "Nameplate Capacity (MW)": "capacity_mw",
        "Retirement Year": "retirement_year", "Retirement Month": "retirement_month"})
    retired = retired[["plant_id", "generator_id", "plant_name", "capacity_mw", "retirement_year", "retirement_month", "source_excel_row"]]
    retired["plant_id"] = retired.plant_id.astype(int)
    retired["generator_id"] = retired.generator_id.astype(str).str.strip()
    if retired.duplicated(["plant_id", "generator_id"]).any():
        raise ValueError("Repeated recent retirement keys; review source before joining.")
    generation_path = project / "data/processed/eia923_generation_scope_audit_2020_01.csv"
    observation_meta_path = tables / "generation_observation_metadata_2020_01.json"
    expected = json.loads(observation_meta_path.read_text())["artifacts_sha256"][str(generation_path.relative_to(project))]
    if checksum(generation_path) != expected:
        raise ValueError("EIA observation audit checksum differs from saved extraction.")
    generation = pd.read_csv(generation_path)
    boundary_path = project / "data/boundaries/california_census_2026.geojson"
    boundary = shape(json.loads(boundary_path.read_text())["features"][0]["geometry"])
    transition, audit, cohort, generators = match_january_plants(december, january, generation, boundary)
    transition = transition.merge(retired[["plant_id", "generator_id", "retirement_year", "retirement_month"]],
                                  on=["plant_id", "generator_id"], how="left", validate="one_to_one")
    artifacts = []
    for name, frame in [("dec2019_ca_wind_snapshot", december), ("jan2020_ca_wind_snapshot", january),
                        ("jan2020_wind_generator_transition", transition), ("jan2020_wind_retirements", retired),
                        ("jan2020_wind_plant_audit", audit), ("jan2020_wind_matched_plants", cohort),
                        ("jan2020_wind_matched_generators", generators)]:
        path = reference / f"{name}.csv"
        frame.to_csv(path, index=False)
        artifacts.append(path)
    summary = []
    for label, frame in [("December all operating-sheet wind", december),
                         ("December OP", december.loc[december.status.eq("OP")]),
                         ("January all operating-sheet wind", january),
                         ("January OP", january.loc[january.status.eq("OP")]),
                         ("Matched stable whole-plant cohort", generators)]:
        summary.append({"stage": label, "generators": len(frame), "plants": frame.plant_id.nunique(),
                        "nameplate_mw": frame.capacity_mw.sum()})
    summary_path = tables / "january_wind_inventory_summary_2020_01.csv"
    pd.DataFrame(summary).to_csv(summary_path, index=False)
    artifacts.append(summary_path)
    total_energy = float(audit.january_net_generation_mwh.sum(min_count=1))
    cohort_energy = float(cohort.january_net_generation_mwh.sum())
    metadata = {
        "status": "Conservative snapshot-stable whole-plant cohort; not measured hourly availability",
        "retrieved_on": args.retrieved_on, "python": platform.python_version(),
        "packages": {p: version(p) for p in ["pandas", "numpy", "openpyxl", "shapely"]},
        "sources": [{"url": "https://www.eia.gov/electricity/data/eia860m/archive/xls/" + name,
                     "sha256": checksum(path)} for name, path in zip(
                         ["december_generator2019.xlsx", "january_generator2020.xlsx"], sources)],
        "monthly_sheet": "Operating", "header_excel_row": 2,
        "retirement_sheet": "Retired; December 2019 and January 2020 dates only",
        "other_inputs_sha256": {str(p.relative_to(project)): checksum(p) for p in [generation_path, observation_meta_path, boundary_path]},
        "whole_plant_rule": "All wind generator keys/statuses/capacities/operation dates/fuel/prime mover unchanged across both snapshots; every unit OP and operating before January; no partial-plant MWh matching",
        "capacity_convention": "Fixed nominal nameplate MW over 744 Pacific-January hours; monthly snapshot agreement is not proof of unreported within-month changes or availability",
        "qa": {"matched_plants": len(cohort), "matched_generators": len(generators),
               "matched_capacity_mw": float(cohort.capacity_mw.sum()),
               "matched_net_generation_mwh": cohort_energy, "CA_EIA923_wind_generation_mwh": total_energy,
               "excluded_EIA923_generation_mwh": total_energy - cohort_energy,
               "cohort_share_of_CA_wind_generation": cohort_energy / total_energy,
               "observed_nominal_monthly_cf": cohort_energy / (float(cohort.capacity_mw.sum()) * 744),
               "out_of_range_observed_plant_cf_count": int(cohort.observed_cf_outside_0_1.sum()),
               "plant_exclusion_counts": audit.loc[~audit.selected].exclusion_reason.value_counts().to_dict()},
        "artifacts_sha256": {str(p.relative_to(project)): checksum(p) for p in artifacts},
    }
    path = reference / "jan2020_wind_inventory_metadata.json"
    path.write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
