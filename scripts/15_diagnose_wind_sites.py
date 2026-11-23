"""Audit annual turbine records and test nearest versus bilinear wind sampling."""

import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path
import platform
import zipfile

import numpy as np
import pandas as pd
import xarray as xr

from energy_events import utc_hourly_index
from january_wind import monthly_bounds
from wind_model import cubic_capacity_factor, published_capacity_factor
from wind_sites import distance_km, sample_wind, turbine_capacity_audit


def checksum(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--eia860-archive", required=True, type=Path)
    parser.add_argument("--wind-data", type=Path)
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--project-dir", type=Path, default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args()
    project = args.project_dir.resolve()
    reference, processed, tables, figures = [project/p for p in ["data/reference", "data/processed", "results/tables", "results/figures"]]
    original_meta = json.loads((reference/"eia2020_ca_wind_metadata.json").read_text())
    if checksum(args.eia860_archive) != original_meta["archive_sha256"]:
        raise ValueError("Use the preserved EIA-860 2020 source archive.")
    inventory_meta_path = reference/"jan2020_wind_inventory_metadata.json"
    inventory_meta = json.loads(inventory_meta_path.read_text())
    for path, expected in inventory_meta["artifacts_sha256"].items():
        if checksum(project/path) != expected:
            raise ValueError("January inventory artifact checksum mismatch.")
    gen_path, plants_path = reference/"jan2020_wind_matched_generators.csv", reference/"jan2020_wind_matched_plants.csv"
    generators, original_plants = pd.read_csv(gen_path), pd.read_csv(plants_path)
    annual_frames = []
    with zipfile.ZipFile(args.eia860_archive) as archive:
        members = {name: archive.read(name) for name in ["3_2_Wind_Y2020.xlsx", "2___Plant_Y2020.xlsx"]}
    for sheet in ["Operable", "Retired and Canceled"]:
        frame = pd.read_excel(BytesIO(members["3_2_Wind_Y2020.xlsx"]), sheet_name=sheet, header=1, engine="openpyxl")
        frame["annual_source_excel_row"] = frame.index + 3
        frame["annual_source_sheet"] = sheet
        annual_frames.append(frame)
    annual = pd.concat(annual_frames, ignore_index=True).rename(columns={"Plant Code":"plant_id", "Generator ID":"generator_id",
        "Nameplate Capacity (MW)":"annual_capacity_mw", "Predominant Turbine Manufacturer":"reported_manufacturer",
        "Predominant Turbine Model Number":"reported_model", "Turbine Hub Height (Feet)":"reported_hub_height_ft"})
    annual["generator_id"] = annual.generator_id.astype(str).str.strip()
    generators["generator_id"] = generators.generator_id.astype(str).str.strip()
    annual["annual_capacity_mw"] = pd.to_numeric(annual.annual_capacity_mw, errors="coerce")
    annual["reported_hub_height_m"] = pd.to_numeric(annual.reported_hub_height_ft, errors="coerce") * .3048
    annual = annual[["plant_id", "generator_id", "annual_capacity_mw", "reported_manufacturer", "reported_model",
                     "reported_hub_height_m", "annual_source_sheet", "annual_source_excel_row"]]
    audit = turbine_capacity_audit(generators, annual)
    audit_path = reference/"jan2020_wind_annual_turbine_audit.csv"
    audit.to_csv(audit_path, index=False)
    accepted_ids = set(audit.loc[audit.whole_plant_capacity_consistent, "plant_id"])
    plants = original_plants.loc[original_plants.plant_id.isin(accepted_ids)].copy()
    kept_generators = audit.loc[audit.whole_plant_capacity_consistent].copy()
    if plants.empty or plants.observed_cf_outside_0_1.any():
        raise ValueError("Require nonempty capacity-consistent cohort with valid observed nominal CFs.")
    cohort_path = reference/"jan2020_wind_capacity_consistent_plants.csv"
    plants.to_csv(cohort_path, index=False)
    plant_source = pd.read_excel(BytesIO(members["2___Plant_Y2020.xlsx"]), sheet_name="Plant", header=1, engine="openpyxl")
    plant_source = plant_source.rename(columns={"Plant Code":"plant_id", "Latitude":"annual_latitude", "Longitude":"annual_longitude"})
    sites = original_plants.merge(plant_source[["plant_id", "annual_latitude", "annual_longitude"]], on="plant_id", how="left", validate="one_to_one")
    for name in ["annual_latitude", "annual_longitude"]:
        sites[name] = pd.to_numeric(sites[name], errors="coerce")
    sites["annual_coordinates_available"] = np.isfinite(sites[["annual_latitude", "annual_longitude"]]).all(axis=1)
    sites["monthly_to_annual_distance_km"] = distance_km(sites.latitude, sites.longitude, sites.annual_latitude, sites.annual_longitude)
    sites["capacity_consistent_subset"] = sites.plant_id.isin(accepted_ids)
    wind_path = args.wind_data or project/"data/raw/data_stream-oper_stepType-instant.nc"
    with xr.open_dataset(wind_path, engine="netcdf4") as source:
        ds = source[["u100", "v100"]].load()
    for name in ["u100", "v100"]:
        if ds[name].attrs.get("units", "").replace(" ", "") not in {"ms**-1", "ms-1", "ms^-1", "m/s"}:
            raise ValueError("Expected wind components in m/s.")
        if ds[name].attrs.get("GRIB_uvRelativeToGrid") != 0:
            raise ValueError("Rotated-grid vectors need explicit handling.")
    times = utc_hourly_index(ds.valid_time.values)
    expected_ends = pd.date_range("2020-01-01T09:00Z", "2020-02-01T08:00Z", freq="h")
    keep = times[1:].isin(expected_ends);ends = times[1:][keep]
    _, iy_all, ix_all = sample_wind(ds, sites, "nearest")
    sites["nearest_latitude"], sites["nearest_longitude"] = ds.latitude.values[iy_all], ds.longitude.values[ix_all]
    sites["nearest_distance_km"] = distance_km(sites.latitude, sites.longitude, sites.nearest_latitude, sites.nearest_longitude)
    sites_path = tables/"wind_site_coordinate_audit_2020_01.csv"
    sites.to_csv(sites_path, index=False)
    manifest_path = reference/"wind_curves/manifest.json"
    manifest = json.loads(manifest_path.read_text())
    for path, expected_hash in manifest["files"].items():
        if checksum(manifest_path.parent/path) != expected_hash:
            raise ValueError("Published curve reference checksum mismatch.")
    capacity = plants.capacity_mw.to_numpy();mw = float(capacity.sum())
    obs = float(plants.january_net_generation_mwh.sum());observed_cf = obs/(mw*744)
    series, rows, diagnostic = pd.DataFrame(index=ends), [], []
    for sampling in ["nearest", "bilinear"]:
        speed, _, _ = sample_wind(ds, plants, sampling)
        for name in ["cubic", *manifest["curves"]]:
            if name == "cubic":power = cubic_capacity_factor(speed)
            else:
                spec = manifest["curves"][name]
                power = published_capacity_factor(speed, pd.read_csv(manifest_path.parent/spec["csv"]), spec["cut_in_wind_speed"], spec["cut_out_wind_speed"])
            hourly = ((power[:-1].astype(float)+power[1:].astype(float))/2)[keep]
            aggregate = hourly @ (capacity/mw)
            series[f"{name}_{sampling}"] = aggregate
            bounds = monthly_bounds(aggregate, ends, mw)
            rows.append({"sampling":sampling, "curve":name, "plants":len(plants), "capacity_mw":mw,
                "observed_monthly_generation_mwh":obs, "observed_monthly_cf_nominal":observed_cf, **bounds,
                "minimum_shortfall_fraction":max(0., obs-bounds["monthly_energy_upper_bound_mwh"])/obs})
            if name == "wtk_iec2":
                for n, plant in enumerate(plants.itertuples()):
                    b = monthly_bounds(hourly[:,n], ends, plant.capacity_mw)
                    diagnostic.append({"sampling":sampling, "plant_id":plant.plant_id, "plant_name":plant.plant_name,
                        "capacity_mw":plant.capacity_mw, "mean_wind_snapshot_m_s":float(speed[:,n].mean()),
                        "observed_monthly_cf_nominal":plant.observed_monthly_cf_nominal,
                        "observed_monthly_generation_mwh":plant.january_net_generation_mwh, **b,
                        "observed_minus_model_upper_mwh":plant.january_net_generation_mwh-b["monthly_energy_upper_bound_mwh"]})
    summary = pd.DataFrame(rows)
    summary_path = tables/"wind_site_sampling_bounds_2020_01.csv";summary.to_csv(summary_path, index=False)
    series_path = processed/"wind_site_sampling_2020_01.csv";series.to_csv(series_path,index_label="interval_end_utc")
    diagnostic_path = tables/"wind_site_iec2_diagnostics_2020_01.csv"
    pd.DataFrame(diagnostic).sort_values(["sampling", "observed_minus_model_upper_mwh"], ascending=[True,False]).to_csv(diagnostic_path,index=False)
    if args.headless:
        import matplotlib
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(10,5))
    for offset, sampling in [(-.1,"nearest"),(.1,"bilinear")]:
        subset = summary.loc[summary.sampling.eq(sampling)]
        low, high = subset.monthly_cf_lower_bound.to_numpy(), subset.monthly_cf_upper_bound.to_numpy()
        mid=(low+high)/2
        ax.errorbar(np.arange(4)+offset,mid,yerr=np.vstack([mid-low,high-mid]),fmt="none",capsize=6,
                    color={"nearest":"tab:blue","bilinear":"tab:orange"}[sampling],label=sampling)
    ax.axhline(observed_cf,color="black",linestyle="--",label="Observed net energy / subset nominal MW / 744 h")
    ax.set_xticks(np.arange(4),["Cubic","WTK IEC I","WTK IEC II","WTK IEC III"])
    ax.set(ylabel="January capacity factor",title="Capacity-consistent subset — grid sampling sensitivity",ylim=(0,.19))
    ax.grid(alpha=.2);ax.legend(loc="lower right",fontsize=9)
    fig.text(.5,.01,"Bars bound nine missing hours only; neither interpolation method resolves subgrid terrain.",ha="center",fontsize=9)
    fig.tight_layout(rect=[0,.04,1,1]);figure_path=figures/"wind_site_sampling_bounds_2020_01.png"
    fig.savefig(figure_path,dpi=180);plt.close(fig)
    known_height = np.isfinite(kept_generators.reported_hub_height_m) & kept_generators.reported_hub_height_m.gt(0)
    metadata = {"status":"Conservative annual-capacity consistency check and spatial sampling sensitivity; not final fleet validation",
        "python":platform.python_version(),"source_retrieved_on":original_meta["retrieved_on"],
        "capacity_rule":"Exclude every plant with any missing annual unit or any monthly/annual capacity difference >1e-6 MW; no inferred reporting consolidation",
        "prior_cohort_plants":len(original_plants),"subset_plants":len(plants),"subset_generators":len(kept_generators),
        "subset_capacity_mw":mw,"subset_generation_mwh":obs,"subset_observed_nominal_cf":observed_cf,
        "excluded_plant_ids":sorted(set(original_plants.plant_id)-accepted_ids),
        "annual_coordinate_match_count":int(sites.annual_coordinates_available.sum()),
        "maximum_monthly_annual_coordinate_distance_km":float(sites.monthly_to_annual_distance_km.max()),
        "nearest_center_distance_median_km":float(sites.nearest_distance_km.median()),
        "nearest_center_distance_maximum_km":float(sites.nearest_distance_km.max()),
        "reported_height_matched_subset_generators":int(known_height.sum()),
        "annual_reported_height_capacity_weighted_mean_m":float(np.average(kept_generators.loc[known_height,"reported_hub_height_m"],weights=kept_generators.loc[known_height,"capacity_mw"])),
        "height_caveat":"End-2020 predominant equipment reports, not proof of January turbine identities. Heights descriptive only; no vertical extrapolation performed.",
        "spatial_caveat":"Bilinear interpolation is applied to u/v before magnitude and curve, not to cell CF. It does not add terrain information or prove more accurate micrositing.",
        "terrain_status":"No surface geopotential/orography or turbine-level/met-mast reference acquired; terrain explanation remains unverified.",
        "wind_checks":"100 m components in m/s, unrotated grid, finite fields, strict hourly chronology; curve and interval conventions preserved",
        "archive_sha256":checksum(args.eia860_archive),"workbook_sha256":{n:hashlib.sha256(b).hexdigest() for n,b in members.items()},
        "input_sha256":{str(p.relative_to(project)):checksum(p) for p in [gen_path,plants_path,inventory_meta_path,manifest_path]},
        "wind_NetCDF_sha256":checksum(wind_path),
        "artifacts_sha256":{str(p.relative_to(project)):checksum(p) for p in [audit_path,cohort_path,sites_path,summary_path,series_path,diagnostic_path,figure_path]}}
    (tables/"wind_site_diagnostic_metadata_2020_01.json").write_text(json.dumps(metadata,indent=2)+"\n")
    print(json.dumps(metadata,indent=2));print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
