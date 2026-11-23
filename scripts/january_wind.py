"""Whole-plant January cohort screening and conservative missing-hour bounds."""

import numpy as np
import pandas as pd
import shapely


def monthly_wind(frame):
    """Normalize CA onshore records, preserving all operating-sheet statuses."""
    selected = frame.loc[frame["Plant State"].eq("CA")
                         & frame.Technology.eq("Onshore Wind Turbine")].copy()
    selected["source_excel_row"] = selected.index + 3
    out = selected.rename(columns={
        "Plant ID": "plant_id", "Generator ID": "generator_id", "Plant Name": "plant_name",
        "Nameplate Capacity (MW)": "capacity_mw", "Status": "status",
        "Latitude": "latitude", "Longitude": "longitude",
        "Operating Month": "operating_month", "Operating Year": "operating_year",
        "Balancing Authority Code": "balancing_authority", "Energy Source Code": "fuel",
        "Prime Mover Code": "prime_mover",
    })
    columns = ["plant_id", "generator_id", "plant_name", "capacity_mw", "status", "latitude",
               "longitude", "operating_month", "operating_year", "balancing_authority",
               "fuel", "prime_mover", "source_excel_row"]
    out = out[columns].copy()
    plant_id = pd.to_numeric(out.plant_id, errors="raise")
    if not (np.isfinite(plant_id) & (plant_id > 0) & (plant_id == np.floor(plant_id))).all():
        raise ValueError("Invalid plant IDs.")
    out["plant_id"] = plant_id.astype(int)
    if out.generator_id.isna().any():
        raise ValueError("Missing generator IDs.")
    out["generator_id"] = out.generator_id.map(lambda value: str(int(value))
        if isinstance(value, (int, float)) and np.isfinite(value) and float(value).is_integer()
        else str(value).strip())
    if out.generator_id.eq("").any() or out.duplicated(["plant_id", "generator_id"]).any():
        raise ValueError("Empty or duplicate generator keys.")
    out["status"] = out.status.astype(str).str.extract(r"^\((\w+)\)", expand=False)
    if out.status.isna().any():
        raise ValueError("Unrecognized monthly status format.")
    for name in ["capacity_mw", "latitude", "longitude", "operating_month", "operating_year"]:
        out[name] = pd.to_numeric(out[name], errors="coerce")
    return out


def match_january_plants(december, january, generation, boundary):
    """Exclude an entire plant if its wind population changes across snapshots.

    Stable month-end records are evidence for a fixed nominal denominator,
    not proof of hourly availability. Do not match partial plant generation.
    """
    keys = ["plant_id", "generator_id"]
    for frame in [december, january]:
        if frame.empty or frame.duplicated(keys).any():
            raise ValueError("Monthly inventories must have unique generator keys.")
    energy = generation.loc[generation.state.eq("CA") & generation.fuel.eq("WND")
                            & generation.prime_mover.eq("WT")].copy()
    if energy.plant_id.duplicated().any():
        raise ValueError("Expected one EIA-923 WND/WT row per physical CA plant.")
    transition = december.merge(january, on=keys, how="outer", suffixes=("_dec", "_jan"),
                                 indicator=True, validate="one_to_one")
    transition["same_snapshot_record"] = transition._merge.eq("both")
    for field in ["status", "capacity_mw", "operating_year", "operating_month", "fuel", "prime_mover"]:
        transition["same_snapshot_record"] &= transition[f"{field}_dec"].eq(transition[f"{field}_jan"])
    records = []
    all_ids = sorted(set(transition.plant_id) | set(energy.plant_id))
    for plant_id in all_ids:
        paired = transition.loc[transition.plant_id.eq(plant_id)]
        current = january.loc[january.plant_id.eq(plant_id)]
        observed = energy.loc[energy.plant_id.eq(plant_id)]
        reason = ""
        if paired.empty:
            reason = "no_CA_wind_monthly_inventory"
        elif not paired.same_snapshot_record.all():
            reason = "wind_records_changed_between_snapshots"
        elif current.empty or not current.status.eq("OP").all():
            reason = "not_all_wind_units_OP_in_both_snapshots"
        elif not (current.fuel.eq("WND") & current.prime_mover.eq("WT")).all():
            reason = "unexpected_fuel_or_prime_mover"
        elif not (np.isfinite(current.capacity_mw) & current.capacity_mw.gt(0)).all():
            reason = "invalid_capacity"
        elif not (current.operating_year.between(1900, 2019)
                  & current.operating_month.between(1, 12)).all():
            reason = "operation_date_does_not_establish_pre_January_service"
        elif (not np.isfinite(current[["latitude", "longitude"]].to_numpy()).all()
              or not current.latitude.between(32, 42).all()
              or not current.longitude.between(-125, -114).all()):
            reason = "invalid_or_out_of_domain_coordinates"
        elif (current.latitude.max() - current.latitude.min() > 1e-6
              or current.longitude.max() - current.longitude.min() > 1e-6):
            reason = "inconsistent_within_plant_coordinates"
        elif not shapely.intersects_xy(boundary, current.longitude.iloc[0], current.latitude.iloc[0]):
            reason = "outside_saved_California_boundary"
        elif observed.empty:
            reason = "no_EIA923_WND_WT_plant_row"
        elif not np.isfinite(observed.january_net_generation_mwh.iloc[0]):
            reason = "missing_January_generation"
        record = {
            "plant_id": int(plant_id),
            "plant_name": current.plant_name.iloc[0] if len(current) else (observed.plant_name.iloc[0] if len(observed) else paired.plant_name_dec.iloc[0]),
            "january_wind_generator_count": len(current),
            "january_wind_capacity_mw": float(current.capacity_mw.sum(min_count=1)),
            "latitude": float(current.latitude.iloc[0]) if len(current) else None,
            "longitude": float(current.longitude.iloc[0]) if len(current) else None,
            "january_net_generation_mwh": float(observed.january_net_generation_mwh.iloc[0]) if len(observed) else None,
            "respondent_frequency": observed.respondent_frequency.iloc[0] if len(observed) else None,
            "has_EIA923_row": bool(len(observed)), "selected": not reason, "exclusion_reason": reason,
        }
        records.append(record)
    audit = pd.DataFrame(records)
    cohort = audit.loc[audit.selected].copy()
    if cohort.empty:
        raise ValueError("No complete plants passed January cohort checks.")
    cohort = cohort.rename(columns={"january_wind_capacity_mw": "capacity_mw"})
    cohort["observed_monthly_cf_nominal"] = cohort.january_net_generation_mwh / (cohort.capacity_mw * 744)
    cohort["observed_cf_outside_0_1"] = ~cohort.observed_monthly_cf_nominal.between(0, 1)
    selected_generators = january.loc[january.plant_id.isin(cohort.plant_id)].copy()
    return transition, audit, cohort, selected_generators


def monthly_bounds(known_cf, interval_ends, capacity_mw):
    """Bound a Pacific-January mean by [0,1] for each missing complete hour."""
    values = np.asarray(known_cf, dtype=float)
    index = pd.DatetimeIndex(interval_ends)
    expected = pd.date_range("2020-01-01T09:00Z", "2020-02-01T08:00Z", freq="h")
    if (values.ndim != 1 or len(values) != len(index) or len(values) == 0
            or str(index.tz) != "UTC" or index.has_duplicates or not index.is_monotonic_increasing
            or not index.isin(expected).all() or not np.isfinite(values).all()
            or not ((values >= 0) & (values <= 1)).all()
            or not np.isfinite(capacity_mw) or capacity_mw <= 0):
        raise ValueError("Require valid Pacific-January hourly CFs and positive nominal capacity.")
    missing = len(expected) - len(index)
    known_sum = float(values.sum())
    return {"known_hours": len(index), "missing_hours": missing, "month_hours": len(expected),
            "known_support_mean_cf": float(values.mean()),
            "monthly_cf_lower_bound": known_sum / len(expected),
            "monthly_cf_upper_bound": (known_sum + missing) / len(expected),
            "monthly_energy_lower_bound_mwh": known_sum * capacity_mw,
            "monthly_energy_upper_bound_mwh": (known_sum + missing) * capacity_mw}


def eia930_january(response):
    """Require one complete UTC-hourly CISO January pair; preserve net negatives."""
    source = response["response"]
    data = pd.DataFrame(source["data"])
    if (source["frequency"] != "hourly" or int(source["total"]) != len(data)
            or len(data) != 1488 or not data.respondent.eq("CISO").all()
            or not data["value-units"].eq("megawatthours").all()
            or set(data.fueltype) != {"WND", "SUN"}):
        raise ValueError("Require complete CISO hourly WND/SUN MWh response, no truncation.")
    data["period"] = pd.to_datetime(data.period, format="%Y-%m-%dT%H", utc=True)
    data["value"] = pd.to_numeric(data.value, errors="raise")
    if not np.isfinite(data.value).all() or data.duplicated(["period", "fueltype"]).any():
        raise ValueError("Missing, duplicate or nonfinite EIA-930 observations.")
    result = data.pivot(index="period", columns="fueltype", values="value").sort_index()
    expected = pd.date_range("2020-01-01T09:00Z", "2020-02-01T08:00Z", freq="h")
    if not result.index.equals(expected) or result.isna().any().any():
        raise ValueError("EIA-930 UTC interval ends do not cover Pacific January exactly.")
    return result.rename(columns={"WND": "eia930_wind_mwh", "SUN": "eia930_solar_mwh"})
