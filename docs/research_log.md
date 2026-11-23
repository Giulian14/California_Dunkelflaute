# California Dunkelflaute research log

This log preserves the decisions and execution evidence needed to write the data, methods, uncertainty, and reproducibility sections of the project. The study target remains California in **2005–2024**; the completed numerical work so far uses **January 2020**.

The log was created on **November 23, 2026**. Earlier entries below are reconstructed from the conversation, preserved scripts, outputs, and repository verification reports. They are not contemporaneous execution diaries, and an exact execution date is not asserted for each early step. Future entries should be added as the work occurs. Git history and the linked records provide the underlying versions.

## Earlier pilot work reconstructed on November 23

| Step | Operation and decision | Saved code or evidence |
| --- | --- | --- |
| 1 | Created a dedicated Conda environment and resolved a Spyder interpreter mismatch between two Anaconda installations. The active project interpreter was verified before analysis. | [Environment notes](environment.md) |
| 2 | Repaired NetCDF access. Initial shared-library and missing-module failures were followed by interpreter correction and successful library imports. Spyder kernel compatibility changed from the 3.0 series to 3.1.7 after an application update. | [Environment notes](environment.md); conversation outputs |
| 3 | Requested hourly ERA5 single-levels for January 2020, variables u100, v100, t2m, ssrd, area [42, −125, 32, −114]. Existing data were reused throughout subsequent work. | [Original request script](../scripts/01_download_era5.py) |
| 4 | Identified a ZIP response despite its `.nc` filename and extracted separate instantaneous and accumulated NetCDF files. The original download script does not perform extraction and is skipped for analysis. | [README data notes](../README.md#data) |
| 5 | Opened both files, checked coordinates, units and expected variables, and verified 744 consecutive hourly timestamps on the 41 × 45 grid. | [Inspection script](../scripts/02_inspect_era5.py); [full verification](full_workflow_verification.json) |
| 6 | Computed 100 m speed from vector components, converted kelvin to Celsius, and divided hourly ssrd accumulations by 3600 to obtain preceding-hour mean irradiance. | [Inspection script](../scripts/02_inspect_era5.py) |
| 7 | Made cosine-latitude-weighted bounding-box weather time series as diagnostics. These include surrounding regions and ocean and are not California averages. | [Bounding-box figure](../results/figures/era5_bounding_box_january_2020.png) |
| 8 | Acquired and preserved a 2026-vintage Census California GeoJSON. Chose a grid-center administrative mask, explicitly including state waters rather than claiming a land-only mask. | [Boundary provenance](boundary_provenance.md) |
| 9 | Built and mapped the mask: 695 selected centers out of 1,845. Preserved a script to rebuild the excluded NetCDF mask. | [Mask script](../scripts/02b_build_california_mask.py) |
| 10 | Recomputed area-weighted weather averages within the mask and saved the 744-row weather CSV and figure. | [Weather script](../scripts/03_california_averages.py); [processed-data notes](../data/processed/README.md) |
| 11 | Implemented an illustrative wind curve with cut-in 3 m/s, rated output at 12 m/s, and shutdown at 25 m/s. Converted at each cell before averaging, assuming uniform capacity per unit area. Mean CF over 744 snapshots was 0.047265. | [Original wind script](../scripts/04_wind_capacity_factor.py) |
| 12 | Implemented the preliminary GHI/1000 solar proxy, clipped to 0–1. Explicitly distinguished normalized irradiance from photovoltaic capacity factor. Mean over 744 hours was 0.116382. | [Proxy script](../scripts/05_solar_resource_proxy.py) |
| 13 | Aligned temporal support by averaging adjacent wind CF snapshots to approximate preceding-hour output. Excluded the first interval without its prior snapshot, leaving 743 intervals. | [Alignment script](../scripts/05b_align_hourly_resources.py) |
| 14 | Tested simultaneous wind and solar values strictly below 0.20. Found 545 low hours, 31 low periods, longest observed duration 19 hours, and zero observed periods ≥24 hours. | [Detection script](../scripts/06_detect_trial_periods.py); [original result tables](../results/tables/trial_low_resource_periods_2020_01.csv) |
| 15 | Added duration sensitivity and edge flags. Identified one truncated initial period: 30 periods are fully observed. Kept the initial 17-hour duration as a lower bound. | [Boundary-aware sensitivity](../results/tables/trial_duration_sensitivity_2020_01.csv) |
| 16 | Assembled the private GitHub repository, preserved uploaded scripts and results, documented input boundaries and requirements, excluded raw NetCDFs and credentials, and checked source/output hashes. | [Results manifest](results_manifest.json); [processed verification](processed_verification.json) |
| 17 | Recreated Python 3.11.11 with seven reported package pins and reran all seven original analysis scripts from the uploaded ERA5 inputs. The mask matched exactly, event tables matched exactly, and small wind CF floating-point differences changed no hourly classifications. | [Full workflow verification](full_workflow_verification.md); [JSON evidence](full_workflow_verification.json) |

The original environment handoff reported Python 3.11.18; the later active-console report was 3.11.11. The reason for that difference is not established. Successful reconstruction used the latter reported version. The direct-package snapshot is not a complete cross-platform environment lockfile.

## November 16 extension work reconstructed from saved records

| Step | Operation and decision | Saved code or evidence |
| --- | --- | --- |
| 18 | Reviewed primary literature. Kept the strict hourly definition as a reference; distinguished it from low 48-hour means of capacity-weighted combined output. Recognized that nighttime low generation is legitimate in the hourly definition and zero prolonged events is a valid result. | [Definition review](event_definitions.md), with Li and Mockert references |
| 19 | Implemented a representative fixed-tilt PV AC model using Erbs decomposition, isotropic transposition, Ross cell temperature, PVWatts DC and inverter output. Assumed 35° south-facing panels, NOCT 45°C, gamma −0.004/°C, DC/AC ratio 1.20, 14% other losses, and 96% nominal inverter efficiency. Used midpoint solar geometry and bracketing temperature snapshots. | [PV method](pv_model.md); [PV helper](../scripts/pv_model.py); [driver](../scripts/07_pv_capacity_factor.py) |
| 20 | Ran 25°, 35° and 45° tilt scenarios using the same 695 centers and 743 intervals. Mean AC CFs were 0.158541, 0.169478 and 0.176466. These are scenario estimates, not observed fleet validation or a year-round tilt optimization. Ten PV tests passed. | [PV verification](pv_model_verification.json); [tilt table](../results/tables/pv_tilt_sensitivity_2020_01.csv) |
| 21 | Compared modeled-PV reference periods: 502 simultaneous low hours at 35° but still no observed 24-hour event. Evaluated 27 combinations of PV tilt, rated-capacity mix, and 48-hour CF threshold. Merged qualifying window supports rather than counting overlapping windows as independent events. | [Comparison script](../scripts/08_compare_event_definitions.py); [event helper](../scripts/energy_events.py) |
| 22 | At 50/50 wind/PV rated capacity and threshold 0.06, minimum 48-hour CF was 0.071207 and no window qualified. At 75% wind, 135 qualifying windows merged into one 199-hour union period. Added conservative edge-context flags. All 22 tests passed; independent calculations agreed for all 27 cases. | [Comparison report](event_comparison.md); [verification](event_comparison_verification.json) |

Versions associated with these earlier stages include full workflow verification commit `676e3e6`, PV extension `7796ddc`, and event comparison `f20920e`. The numerical records and methods above are preserved; later scenarios do not overwrite those findings.

## November 23 wind curve and geographic weighting assessment

### Question and controlled design

Determine how much the January wind estimates and energy-event results depend on (a) the power curve and (b) geographic deployment. Hold the ERA5 winds at 100 m, time interval convention, and 35° area-weighted PV scenario fixed. Compare four curves × two wind weightings, without tuning thresholds or fitting generation data.

### Inputs and source decisions

- Preserved the WTK IEC I, II and III normalized onshore curves and their specifications from the official turbine-models archive at commit `e9e4ccc6a87f50c0c65d236154a2897e752c47c9`. The archive identifies these theoretical reference models with 100 m hub height. Retained its BSD license, original CSV/YAML files and checksums.
- Retrieved the official EIA-860 2020 annual ZIP and joined the `3_2_Wind_Y2020.xlsx` Operable sheet to coordinates in `2___Plant_Y2020.xlsx`. Selected California onshore generators with status OP, positive nameplate MW and valid in-boundary coordinates. Reported out-of-service rows separately.
- Retained **117 generator records at 101 plants, totaling 5,916.5 MW**. Excluded **five out-of-service records totaling 54.1 MW**. All retained points passed geographic screening and collapsed to **25 nearest ERA5 centers**. No retained point mapped to a center outside the administrative mask.
- Treated this as a **fixed end-of-2020 reference layout**, not the fleet or available capacity during every January 2020 hour. The archive instructions define existing-equipment status at the end of the reporting year. Reported heights average **73.26 m**, capacity-weighted; they are not substituted for the controlled 100 m wind input.
- The USGS download and legacy endpoints returned HTTP 403, so they were not used as data inputs. The EIA archive URL was obtained from the official landing page; an initial non-archive URL returned HTML and was rejected as non-ZIP. The validated archive, member hashes, derived tables and screening rules are recorded in the EIA metadata.

### Model and weighting decisions

- Retain the original cubic curve for direct comparison. Interpolate each published curve linearly between its tabulated speeds, with zero output below cut-in and strictly above its documented cut-out. Preserve tabulated endpoint values. This avoids an artificial ramp after the IEC III shutdown at 22 m/s.
- Uniform weighting uses cosine-latitude area weights at the 695 administrative centers. Location weighting sums plant nameplate MW at each nearest center and divides by total MW; it does **not** multiply these capacity shares by latitude weights again.
- Apply the curve at each grid cell before spatial aggregation. Average adjacent aggregate wind CF snapshots once to approximate hourly means. The two averaging operations commute with fixed spatial weights, but the nonlinear power conversion must precede aggregation.
- Use no explicit density correction, wake loss, availability loss, or hub-height adjustment. The published curves are reference scenarios, not fitted models of the specific EIA generators. Leave the PV geographic distribution unchanged to isolate the wind factors.

### Results over 743 complete hourly intervals

| Wind curve | Uniform area weights | EIA capacity-location weights |
| --- | ---: | ---: |
| Original cubic | 0.047307 | 0.057431 |
| WTK IEC I | 0.058478 | 0.074495 |
| WTK IEC II | 0.074876 | 0.099237 |
| WTK IEC III | 0.090360 | 0.125612 |

All eight scenarios still have zero observed 24-hour simultaneous events, and zero baseline 48-hour events at 50/50 rated capacity and threshold 0.06. Wind-heavy portfolio sensitivities differ: the IEC II/capacity-location case has two observed union periods at 75% wind and 0.06, one with incomplete edge context. This is definition/model sensitivity, not observed validation.

### Code, outputs and verification

- [Inventory preparation](../scripts/00_prepare_eia_wind_inventory.py), [wind helper](../scripts/wind_model.py), and [assessment driver](../scripts/09_assess_wind_model.py).
- [Sources and method](wind_assessment.md), [scenario summary](../results/tables/wind_assessment_summary_2020_01.csv), [72 event sensitivities](../results/tables/wind_assessment_event_sensitivity_2020_01.csv), and [figure](../results/figures/wind_model_geography_assessment_2020_01.png).
- [Verification record](wind_assessment_verification.json) and run metadata document source hashes, regression agreement, independent weight/power checks, tests, and outputs. Raw archives, spreadsheets, and NetCDF inputs are not committed.

### Remaining decisions before a long-term result

The 2020 layout and the generic 100 m curves are reference scenarios. Comparing with observed generation is still required before making accuracy claims. ERA5 at 0.25° cannot resolve turbine micrositing, and 101 plant points do not supply 101 independent weather samples when they occupy 25 cells. PV siting and other physical losses remain separate assumptions. Multi-year processing must use contiguous data and appropriate event-edge context; no 2005–2024 climatology has yet been calculated.

## How to use this record for the paper

Use the linked source and algorithm records to write a reproducible methods narrative. Summarize the original proxy as a pilot, then explain the selected final physical models and event definitions. Keep alternative scenarios in a sensitivity subsection. Put environment troubleshooting and detailed execution history in a reproducibility appendix rather than presenting each interactive-console action as a scientific method.

Before final writing, check every reported number against the matching scenario, interval support, denominator, source version and verification record. Preserve the distinction between modeled energy availability, actual generation, climatological rarity and electricity adequacy.
