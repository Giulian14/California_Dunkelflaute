"""Extract January 2020 CAISO/EIA observations from separately downloaded files."""

import argparse
import hashlib
from importlib.metadata import version
from io import BytesIO
import json
from pathlib import Path
import zipfile
import platform

import numpy as np
from openpyxl import load_workbook
import pandas as pd

from observed_generation import hourly_production, january_starts


def checksum(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--caiso-workbook", required=True, type=Path)
    parser.add_argument("--eia923-archive", required=True, type=Path)
    parser.add_argument("--retrieved-on", required=True, type=str)
    parser.add_argument("--project-dir", type=Path, default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args()
    from datetime import date
    date.fromisoformat(args.retrieved_on)
    project = args.project_dir.resolve()
    processed, tables = project / "data/processed", project / "results/tables"
    processed.mkdir(parents=True, exist_ok=True)
    tables.mkdir(parents=True, exist_ok=True)
    with args.caiso_workbook.open("rb") as source:
        workbook = load_workbook(source, read_only=True, data_only=True)
        iterator = workbook["Production"].values
        header = next(iterator)
        if header[:6] != ("Date", "Hour", "Interval", "Load", "Solar", "Wind"):
            raise ValueError("Unexpected CAISO production schema.")
        rows = [row[:6] for row in iterator if row[0] is not None
                and row[0].year == 2020 and row[0].month == 1]
        production = pd.DataFrame(rows, columns=header[:6])
        starts = january_starts(production.Date, production.Hour, production.Interval)
        # In Production, Date includes each five-minute start; verify all fields agree.
        reconstructed_wall = starts.tz_convert("America/Los_Angeles").tz_localize(None)
        if not reconstructed_wall.equals(pd.DatetimeIndex(production.Date)):
            raise ValueError("CAISO Date and market-hour/interval fields disagree.")
        expected = pd.date_range("2020-01-01 08:00", "2020-02-01 08:00", freq="5min",
                                 inclusive="left", tz="UTC")
        if not starts.equals(expected):
            raise ValueError("CAISO January production is incomplete, duplicated or unordered.")
        five = pd.DataFrame({"solar_production_mw": production.Solar.to_numpy(dtype=float),
                             "wind_production_mw": production.Wind.to_numpy(dtype=float)}, index=starts)
        iterator = workbook["Curtailments"].values
        if next(iterator) != ("Date", "Hour", "Interval", "Wind Curtailment", "Solar Curtailment"):
            raise ValueError("Unexpected CAISO curtailment schema.")
        rows = [row for row in iterator if row[0] is not None
                and row[0].year == 2020 and row[0].month == 1]
        workbook.close()
    curtailment = pd.DataFrame(rows, columns=["date", "hour", "interval", "wind", "solar"])
    curtail_starts = january_starts(curtailment.date, curtailment.hour, curtailment.interval)
    if curtail_starts.has_duplicates or not curtail_starts.isin(starts).all():
        raise ValueError("Duplicated or out-of-production-range curtailment timestamps.")
    for fuel in ["wind", "solar"]:
        # Source lists only intervals with curtailment. Blank cells mean no
        # curtailment for that fuel, not a missing production observation.
        values = pd.to_numeric(curtailment[fuel].replace("", 0), errors="raise").fillna(0)
        if not np.isfinite(values).all() or (values < 0).any():
            raise ValueError("Invalid curtailment MW.")
        sparse = pd.Series(values.to_numpy(), index=curtail_starts)
        five[f"{fuel}_curtailment_mw"] = sparse.reindex(starts, fill_value=0)
    hourly = hourly_production(five)
    caiso_path = processed / "caiso_generation_hourly_2020_01.csv"
    hourly.to_csv(caiso_path, index_label="interval_end_utc")

    with zipfile.ZipFile(args.eia923_archive) as archive:
        member = "EIA923_Schedules_2_3_4_5_M_12_2020_Final_Revision.xlsx"
        member_bytes = archive.read(member)
    data = pd.read_excel(BytesIO(member_bytes), sheet_name="Page 1 Generation and Fuel Data",
                         header=5, engine="openpyxl")
    rename = {
        "Plant Id": "plant_id", "Plant Name": "plant_name", "Plant State": "state",
        "Reported\nPrime Mover": "prime_mover", "Reported\nFuel Type Code": "fuel",
        "Balancing\nAuthority Code": "balancing_authority", "Respondent\nFrequency": "respondent_frequency",
        "Netgen\nJanuary": "january_net_generation_raw", "YEAR": "year",
    }
    selected = data.loc[(data["Plant State"].eq("CA") | data["Balancing\nAuthority Code"].eq("CISO"))
                        & data["Reported\nFuel Type Code"].isin(["WND", "SUN"]), list(rename)].rename(columns=rename)
    selected.insert(0, "source_excel_row", selected.index + 7)
    if not selected.year.eq(2020).all():
        raise ValueError("Unexpected EIA reporting year.")
    selected["january_net_generation_mwh"] = pd.to_numeric(selected.january_net_generation_raw, errors="coerce")
    selected["january_value_available"] = selected.january_net_generation_mwh.notna()
    selected["is_state_fuel_increment"] = selected.plant_id.eq(99999) | selected.plant_name.eq("State-Fuel Level Increment")
    # Retain '.'/other missing values rather than silently treating them as zero.
    inventory_path = project / "data/reference/eia2020_ca_wind_plants.csv"
    inventory = pd.read_csv(inventory_path)
    selected["in_prior_wind_reference_inventory"] = selected.plant_id.isin(inventory.plant_id) & selected.fuel.eq("WND")
    eia_path = processed / "eia923_generation_scope_audit_2020_01.csv"
    selected.to_csv(eia_path, index=False)
    summary_rows = []
    for scope, subset in [("California state", selected.loc[selected.state.eq("CA")]),
                          ("EIA reported CISO BA", selected.loc[selected.balancing_authority.eq("CISO")])]:
        for (fuel, mover), group in subset.groupby(["fuel", "prime_mover"]):
            summary_rows.append({
                "scope": scope, "fuel": fuel, "prime_mover": mover, "source_rows": len(group),
                "plants_excluding_state_fuel_increment": group.loc[~group.is_state_fuel_increment, "plant_id"].nunique(),
                "state_fuel_increment_rows": int(group.is_state_fuel_increment.sum()),
                "available_january_generation_mwh": group.january_net_generation_mwh.sum(min_count=1),
                "missing_january_rows": int(group.january_net_generation_mwh.isna().sum()),
                "annual_respondent_rows": int(group.respondent_frequency.eq("A").sum()),
            })
    summary_path = tables / "eia923_generation_scope_summary_2020_01.csv"
    pd.DataFrame(summary_rows).to_csv(summary_path, index=False)
    matched = selected.loc[selected.in_prior_wind_reference_inventory]
    metadata = {
        "retrieved_on": args.retrieved_on,
        "python": platform.python_version(),
        "packages": {name: version(name) for name in ["numpy", "pandas", "openpyxl"]},
        "prior_wind_inventory_sha256": checksum(inventory_path),
        "sources": [
            {"url": "https://www.caiso.com/documents/productionandcurtailmentsdata_2020.xlsx",
             "sha256": checksum(args.caiso_workbook), "sheets": ["Read_me", "Production", "Curtailments"]},
            {"url": "https://www.eia.gov/electricity/data/eia923/archive/xls/f923_2020.zip",
             "sha256": checksum(args.eia923_archive), "member": member,
             "member_sha256": hashlib.sha256(member_bytes).hexdigest(),
             "sheet": "Page 1 Generation and Fuel Data", "header_excel_row": 6},
        ],
        "caiso_units": "Five-minute MW aggregated by arithmetic mean; hourly MW equals hourly MWh numerically",
        "caiso_time_assumption": "Production Date is interval start in Pacific market time; Hour 1 starts at 00:00; interval 1 starts at minute 0. January only, UTC-08:00. Date and Hour/Interval checked for agreement; workbook Read_me does not explicitly name a timezone.",
        "caiso_raw_quality": "Source is reviewed raw production data, not operational or settlement-quality data",
        "caiso_curtailment_handling": "Separate columns; unlisted/blank curtailments zero per sparse-table description. Never filled missing production or added curtailment to generation.",
        "five_minute_production_rows": len(five), "hourly_observations": len(hourly),
        "negative_production_value_counts": {name: int((five[name] < 0).sum()) for name in ["wind_production_mw", "solar_production_mw"]},
        "full_local_january_energy_mwh": {name: float(hourly[name].sum()) for name in hourly},
        "eia_scope": "CA-state or EIA-reported CISO BA; WND, SUN. Solar PV=prime mover PV; solar thermal kept separately.",
        "eia_monthly_caveat": "Annual respondents are flagged; monthly entries in annual-final files must not all be described as direct monthly reports. Missing values preserved.",
        "eia_state_fuel_increments": "Synthetic plant ID 99999 / State-Fuel Level Increment retained and flagged for scope totals; excluded from plant counts and inventory matches.",
        "prior_wind_inventory_matched_plants": int(matched.plant_id.nunique()),
        "prior_wind_inventory_unmatched_plant_ids": sorted(set(inventory.plant_id) - set(matched.plant_id)),
        "matched_inventory_generation_mwh_available": float(matched.january_net_generation_mwh.sum(min_count=1)),
        "artifacts_sha256": {str(path.relative_to(project)): checksum(path) for path in [caiso_path, eia_path, summary_path]},
    }
    (tables / "generation_observation_metadata_2020_01.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
