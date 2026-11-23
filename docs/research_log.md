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

## November 23 first observed-generation comparison

### Purpose, inputs and scope decision

Begin checking modeled wind/PV behavior against official generation records before selecting a final model or processing 2005–2024. Downloaded CAISO's 2020 Production and Curtailments XLSX and EIA-923's 2020 annual-final revision ZIP from their official archive pages. Recorded archive/member SHA-256 hashes and retrieval date. Reused the existing Python 3.11.11 wind environment (including openpyxl 3.1.5); no new dependency installation or ERA5 download was needed.

CAISO's balancing area is not the California state mask or the fixed EIA wind inventory. EIA's reported-CISO population also does not reconcile numerically with the CAISO raw archive. Therefore this stage is a **temporal-shape benchmark across unmatched fleets**, not a validation of CF magnitudes or event classifications. No lag, gain, curve, loss factor or threshold was fitted to the observations.

### Processing and quality decisions

- Interpreted January CAISO market hours as Pacific interval starts, checked Production Date against Hour/Interval for every row, converted to UTC, and averaged twelve five-minute MW values into each preceding-hour mean. The workbook does not explicitly name the timezone; this interpretation is recorded as an assumption. Rejected gaps/duplicates/partial hours; restricted the importer to January 2020 so DST ambiguity cannot be silently resolved.
- Retained **8,928 five-minute observations / 744 complete hours**. Kept reported curtailment separate from production, with zeros only for unlisted/blank entries in the documented sparse curtailment table. January curtailment sums round to **7,933 MWh wind** and **130,070 MWh solar**, matching the separate published monthly report's rounded totals. Its production maxima differ from this raw workbook, so no general reconciliation is claimed.
- Intersected actual interval supports: **735 common hours**, ending January 1 09:00 UTC through January 31 23:00 UTC. Eight existing model intervals precede the Pacific observation month; nine observed end-of-month hours lack model data. Used only **30 complete Pacific days** for daily comparisons, assigning midnight end labels to the preceding local date.
- Extracted **767** EIA source rows for California-state or CISO-BA wind/solar scope checks. Preserved respondent frequency, missing January values, and source Excel row numbers. Detected three synthetic `State-Fuel Level Increment` PV rows under ID 99999; kept them flagged in state totals but excluded them from physical plant counts. All **101** prior wind-reference plant IDs match EIA wind records, totaling **757,441.835 MWh** in January; a plant-ID join alone does not establish generator-level availability or a January capacity denominator.
- Calculated hourly and daily correlations and own-mean-scaled dimensionless RMSE. This removes amplitude and must not be described as CF accuracy. Added a daylight-only PV correlation and hourly first-difference correlations to expose limits of apparent agreement.

### Findings and interpretation

With the same cubic wind curve, changing from uniform to capacity-location weights raises hourly correlation with CAISO wind from **0.341 to 0.783**, and daily-mean correlation from **0.503 to 0.883**. IEC II/location gives **0.796 hourly / 0.888 daily**, but only **0.245** for adjacent hourly differences. These support the relevance of deployment geography for shape; they do not select a best curve or establish amplitude accuracy.

PV correlation is **0.969 hourly**, **0.912** over 316 positive-modeled-PV hours, and **0.641** across complete daily means. The shared day–night cycle contributes strongly to hourly agreement. Fixed-tilt versus fleet technology/siting differences and operations remain unmodeled. One autocorrelated month is not independent long-term validation.

### Implementation, verification and saved evidence

Added [observation preparation](../scripts/10_prepare_generation_observations.py), [shape comparison](../scripts/11_compare_observed_shapes.py), [helpers](../scripts/observed_generation.py), and [nine tests](../tests/test_observed_generation.py). All **42 tests** and `pip check` passed. A test initially exposed a pandas timestamp-resolution assumption; duration checks were corrected to compare timedeltas rather than assume integer timestamps always use nanoseconds.

Independent streaming Excel/array calculations verified the source selection, all hourly aggregates, energy conservation, curtailments, paired support, local-day grouping and all nine scenario metric rows. Source and artifact hashes were checked, and the figure was visually reviewed. See the [method and scope report](observed_generation_comparison.md), [verification record](observed_generation_verification.json), [metrics](../results/tables/observed_shape_metrics_2020_01.csv), [EIA scope summary](../results/tables/eia923_generation_scope_summary_2020_01.csv), and [figure](../results/figures/observed_generation_shapes_2020_01.png).

Before amplitude validation, reconcile observation populations, reconstruct a January-specific operating inventory, match plant/technology/AC-capacity denominators, and obtain missing boundary weather hours. Then test a separate period. Original pilot/PV/event/wind artifacts and event thresholds remain unchanged.

## November 23 January inventory match, energy bounds and source cross-check

### Objective and source acquisition

Move beyond BA-wide shape comparison by matching monthly plant generation to an appropriate January wind inventory. Retrieved official EIA-860M December 2019 and January 2020 XLSX snapshots; reused the existing EIA-923 extraction, California boundary, ERA5 wind/mask inputs and reference curves. Verified workbook titles and saved source/member/output checksums. Reused the clean Python 3.11.11 wind environment without package installation or another ERA5 download.

For the unresolved source-population discrepancy, made a small official EIA-930 API request for CISO wind and solar over Pacific January (1,488 hourly values) using the public demo key. Also saved route metadata, whose hourly description explicitly specifies UTC. Retrieved the official OMB-hosted EIA-923 form to check reporting requirements. An older instruction-PDF mirror returned HTTP 403 and was not used as an input; the official form's Schedule 3D establishes that annual wind/solar respondents provide operations for each month. An annual-frequency flag alone does not imply an estimated allocation or annual-only generation.

### Inventory decisions and exclusions

The December operating sheet has 137 wind records / 117 plants / 6,166.2 MW, of which OP records total 6,148.7 MW. January has 131 records / 112 plants / 6,099.5 MW, of which 129 OP records at 111 plants total 6,082.0 MW. These differ from the preserved end-2020 reference inventory; it is not silently replaced.

Six generator keys disappear across snapshots. The January Retired sheet dates five retirements totaling 64.9 MW to January 2020, and one 1.8 MW retirement to December 2019. Thus snapshot disappearance is not synonymous with a January retirement. Exclude any whole plant whose wind unit set/status/capacity/operation-date/fuel/prime-mover records change, whose wind units are not all OP before January, or whose coordinates/generation cannot be matched. This prevents dividing a whole plant's generation by only its surviving units. Three otherwise stable plants (50823, 52143, 52144; 86.5 MW) lack an EIA-923 WND/WT match; no inferred aliases or successor IDs are substituted.

The final cohort has **106 plants / 123 generators / 5,985.7 MW**, with **759,921.181 MWh** of January net generation, or **99.6000%** of the EIA CA-state wind total. Excluded EIA rows sum to **3,051.580 MWh**; the energy ledger closes exactly to numerical precision. The cohort occupies **24 ERA5 centers**; none of their nearest centers falls outside the administrative mask. All observed plant nominal CFs are in 0–1. The fixed denominator is installed nameplate MW × 744 h, not measured available capacity. Snapshot stability does not prove hourly availability or exclude unreported within-month changes.

### Model/time-support decisions and findings

Assigned each retained plant's nominal MW to its nearest grid center, without an extra cosine-latitude factor. Kept all four wind curves, the 100 m input, and nonlinear-before-averaging convention. Averaged adjacent wind CF snapshots once. The known model series supplies **735** Pacific-January intervals; **nine** end-of-month hours are absent. Instead of fabricating weather or assuming zero output, bounded every missing hourly CF by 0–1. Full-month bounds are known-CF-sum/744 and (known-CF-sum+9)/744; they cover missing support only, not all model uncertainty.

Observed matched nominal monthly CF is **17.0640%**. Model monthly CF bounds are **5.69–6.90% cubic**, **7.38–8.59% IEC I**, **9.83–11.04% IEC II**, and **12.44–13.65% IEC III**. Every model upper bound is below observed net generation. IEC II's upper energy bound is **491,592.763 MWh**, at least **268,328.418 MWh / 35.31%** below observed energy even if all missing hours generate at full capacity. This is a material model-validation warning under the cohort/time/capacity assumptions. Strong prior shape correlation did not establish correct energy amplitude. No fitted gain, curve selection, additional loss factor or event-threshold adjustment was made.

### Operational-source audit

EIA-930 CISO wind totals **1,002,027 MWh**, **1.0571%** above CAISO's raw **991,545.496 MWh**, with hourly correlation **0.9858**. EIA-930 solar totals **1,493,359 MWh**, **4.1580%** below CAISO, correlation **0.9675**. Preserved **382 negative EIA net-solar hours**, with no clipping. Both operational wind totals remain substantially above EIA-923's reported-CISO **748,408.868 MWh**. Operational/plant-survey population and physical/commercial accounting definitions are documented; no specific cause or numerical reconciliation has been established, and no correction factor was imposed. Use matched EIA-923 plants for the amplitude diagnostic, rather than either BA-wide operational series divided by statewide capacity.

### Code, verification and evidence

Added [cohort preparation](../scripts/12_match_january_wind_inventory.py), [bounded comparison](../scripts/13_bound_matched_wind_generation.py), [source audit](../scripts/14_audit_generation_sources.py), [helpers](../scripts/january_wind.py) and [14 scientific/integrity tests](../tests/test_january_wind.py). All **56 tests** passed. Independent original-workbook and array calculations reproduced the 106 plants, 123 generators, capacity/energy ledger, six retirement matches, all four power series, all **424 plant/curve bounds**, and all **1,488** API values. Published-curve series agreed within 1.7e-16; source/output hashes were checked and the bounds figure was visually reviewed.

Saved the [full method and findings](january_wind_match.md), [inventory metadata](../data/reference/jan2020_wind_inventory_metadata.json), [bounds](../results/tables/matched_january_wind_bounds_2020_01.csv), [source totals](../results/tables/generation_source_monthly_audit_2020_01.csv), [figure](../results/figures/matched_january_wind_bounds_2020_01.png), and [verification record](january_wind_verification.json). Raw workbooks, API responses and ERA5 inputs remain outside Git.

### Consequence for the research plan

Investigate grid-scale wind/terrain representation at high-capacity sites, centroid versus turbine locations, and actual turbine/hub specifications before selecting/calibrating a long-term wind model. Boundary weather can narrow the bounds but cannot resolve this shortfall under the current reference assumptions. Earlier event counts remain preserved conditional scenario results, not validated climatological estimates. Neither the full 2005–2024 run nor a solar-amplitude validation was started in this stage.

## November 23 wind-site diagnostics and expansion-readiness review

### Scope and important refinement of the previous plant match

Continue investigating the wind energy shortfall and identify what must be checked before expanding to 2005–2024. Reused the same EIA-860 2020 ZIP, January cohort, original ERA5 wind and curve files; no weather download, new dependency or credential was required. The annual wind workbook contains both Operable and Retired and Canceled sheets, allowing all 123 January generators to be joined by their original keys.

The additional join found capacity disagreements at **50821/GEN1 (48.0 versus 88.5 MW)**, **52142/GEN1 (29.0 versus 75.0 MW)** and **55719/GENI (44.4 versus 42.6 MW)**. The first two increases exactly equal capacities of the three previously unmatched Mojave plants. This suggests reporting consolidation and makes the earlier monthly-snapshot match insufficient as proof of comparable generation populations. No asset merge or allocation was inferred. Excluded each affected whole plant, including Mountain View's other unchanged 22.2 MW unit. The old 106-plant numerical artifacts are preserved but the original report and README now explicitly qualify them.

The stricter **capacity-consistent subset** has **103 plants / 119 generators / 5,842.1 MW**, with **735,337.752 MWh** and nominal observed monthly CF **16.9178%**. Capacity consistency does not prove complete asset lineage or hourly availability. This is the most conservative available diagnostic, not a finished historical operating-fleet reconstruction.

### Coordinates, turbine information and wind mechanics

Compared monthly and annual plant coordinates: all **106** matched, maximum difference **0.00413 km** (about four metres). Nearest ERA5-center distances have median **10.44 km** and maximum **17.13 km**. The two EIA sources may share underlying coordinates, so this does not independently validate turbine micrositing.

All 119 retained generators have positive end-2020 reported hub heights; January-MW-weighted mean height is **73.81 m**. Retained predominant manufacturer/model and source sheet/row. These annual descriptors are not confirmed January equipment configurations; no height adjustment or equipment-specific power curve was silently substituted. No surface geopotential/orography, met-mast or turbine-level independent wind source was acquired, so a terrain explanation remains unverified.

Checked 100 m vector-component units, unrotated-grid flags, finite fields and UTC chronology. Compared nearest-cell sampling with bilinear interpolation of **u and v before magnitude and power conversion**, preserving endpoint averaging once. Bilinear interpolation adds no subgrid terrain information.

### Results and implications

The subset's IEC II monthly bounds are **9.85–11.06% nearest-center** and **8.68–9.89% bilinear**, versus **16.92%** observed nominal CF. The corresponding minimum energy shortfalls are **34.65%** and **41.53%**, even with missing-hour upper bounds. All eight curve/sampling cases remain below observed energy. Neither capacity refinement nor this interpolation alternative resolves the shortfall. No fitted gain, curve parameter, loss factor or event threshold was introduced.

Saved plant-level diagnostics to prioritize investigation. Voyager Wind II, Tule Wind, Shiloh I and Shiloh 2 have the largest positive nearest-center IEC II residuals against model upper bounds. These identify sites to inspect, not proven causes of bias. Prior event counts remain conditional modeled scenarios.

### Verification, outputs and next checks

Added [site helper](../scripts/wind_sites.py), [driver](../scripts/15_diagnose_wind_sites.py), [seven tests](../tests/test_wind_sites.py), [method](wind_site_diagnostics.md) and [expansion-readiness record](expansion_readiness.md). All **63 tests** passed. Independent source joins and manual four-corner vector interpolation checked the 103/119 subset, all eight power time series, all **206** IEC II plant/sampling cases, and agreement of nearest bounds with aggregation of the preserved earlier per-plant results. Source/output checksums and [verification](wind_site_verification.json) are retained; the figure was visually reviewed.

The readiness record lists remaining wind physics/asset-lineage validation, plant-matched PV amplitudes, contrasting-season/held-out-year checks, fixed-versus-evolving fleet choice, full input/time-support QC, chunk equivalence across months/years/leap days, event-definition sensitivity and temperature-reference design. A proposed UTC 2005–2024 core has **175,320 complete hourly intervals**, requiring appropriate endpoint samples and external window/event context. No 20-year processing was started.

## How to use this record for the paper

Use the linked source and algorithm records to write a reproducible methods narrative. Summarize the original proxy as a pilot, then explain the selected final physical models and event definitions. Keep alternative scenarios in a sensitivity subsection. Put environment troubleshooting and detailed execution history in a reproducibility appendix rather than presenting each interactive-console action as a scientific method.

Before final writing, check every reported number against the matching scenario, interval support, denominator, source version and verification record. Preserve the distinction between modeled energy availability, actual generation, climatological rarity and electricity adequacy.
