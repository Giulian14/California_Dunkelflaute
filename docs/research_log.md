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

## November 23 terrain-reference and curve-provenance audit

### Purpose and source decisions

Continue checking wind-model assumptions before expansion. Manufacturer V90 PDF links hosted by Maine, Taiwan's NDC and the Dutch environmental-assessment archive returned HTTP 403. Their search snippets/tables were not treated as verified curve data. Audited the existing turbine archive instead, retaining its immutable commit and original spec/blob hashes, and pursued accessible terrain references without changing resource models.

Retrieved public WeatherBench 2 ERA5 metadata and five static-field/coordinate chunks at the exact 0.25° grid (geopotential, orography standard deviation, land–sea fraction, latitude, longitude). Compressed chunk transfer totaled **4,826,687 bytes**, not a global dynamic weather download. Queried USGS EPQS for **103** selected plant coordinates in metres/EPSG:4326, retaining raw responses, raster IDs, reported resolutions and acquisition dates. All 103 responses were valid. Source URLs, object generations, checksums and retrieval date are in the committed terrain manifest; raw binary chunks and API responses remain outside Git.

Created a separate clean Python **3.11.11** environment with the existing wind requirements plus **numcodecs 0.16.6** for Blosc decoding. Saved the resolved 34-package snapshot; `uv pip check` passed. The uv-created environment has no pip module, so package consistency was checked with uv. Earlier environments and all prior scientific outputs were preserved. Updated current full-suite instructions to use the extension requirements; historical PV checks can still be run separately.

### Terrain calculations and findings

Validated single-chunk Zarr layout/byte counts, source units and exact grid-center identity, including negative-to-positive longitude conversion. Converted geopotential to geopotential height with **g=9.80665 m/s²**. Compared that grid reference to DEM point elevations, explicitly retaining different spatial support, vertical definitions and plant-centroid versus turbine-location limitations.

The 103 plants share **24 weather centers**. Signed point-minus-grid height has median **−35.81 m**, median absolute difference **205.23 m**, and range **−936.06 to +517.30 m**. Sampled orography standard deviation ranges **49.32–403.48 m**. Voyager Wind II and Tule Wind have point/grid differences of **+148.70 m** and **+283.82 m**, but Shiloh I and Shiloh 2 show large wind residuals with differences of only **+3.14 m** and **+18.43 m**. Thus elevation offset alone does not explain the shortfall. No wind-height shift, speed scaling, regression fit, independent-sample p-value or causal terrain attribution was made. Independent hub-height wind data remain unavailable in this stage.

### Turbine-curve provenance findings

The 119-generator subset has **49 manufacturer/model groups**. Conservative same-name candidates in the pinned archive cover only Vestas V47-660 and V27-225, **248.4 MW / 4.2519%** of capacity; whole plants covered by those candidates total **226.9 MW**. Both archived specs label curves theoretical and have empty primary-reference lists. They are not manufacturer-validated January curves. V27 is archived as Distributed; similar ratings/rotors do not justify mapping DOE GE research references to commercial GE models. No candidate does not imply a curve is unavailable elsewhere. No new power curve or resource/event output was substituted.

### Automation, verification and records

Added [terrain preparation](../scripts/16_audit_wind_terrain.py), [manifest replay](../scripts/16a_fetch_terrain_references.py), [curve audit](../scripts/17_audit_curve_coverage.py) and scientific helpers/tests. Replayed the recorded manifest with **110 files verified from cache and zero downloads**. Changed bytes are rejected rather than silently overwriting a source version. All **72 tests** passed. Independent grid-index formulas/direct DEM values reproduced all 103 point/grid comparisons and summaries; independent literal-label accounting reproduced all 49 model groups and candidate capacities. Source/output checksums and the [verification record](terrain_curve_verification.json) are retained; the figure was visually reviewed and its colorbar placement corrected before publication.

Saved [method and limits](wind_terrain_and_curve_audit.md), [site table](../results/tables/wind_terrain_site_audit_2020_01.csv), [figure](../results/figures/wind_terrain_comparison_2020_01.png), [curve-coverage table](../results/tables/turbine_curve_candidate_coverage_2020_01.csv), original candidate specs/BSD notice and the Copernicus license. Outputs carry the required C3S attribution and EC/ECMWF responsibility statement; USGS is credited for the DEM reference.

The [readiness record](expansion_readiness.md) now distinguishes acquired terrain context from still-open independent wind, turbine provenance, PV-amplitude, held-out-period and temporal-continuity checks. No 2005–2024 climatology or calibrated wind-model claim was produced.

## November 24 weather-file and event continuity verification

### Objective and processing design

Verify that file boundaries do not become weather-interval or event boundaries before extending the archive. Added a reusable iterator that reads consecutive, nonoverlapping weather pairs, carries one preceding instantaneous/accumulated record, and models complete hours without dropping an hour at every join. Only the globally initial unbracketed record is unavailable. Reject gaps, overlaps, changed grids/units/dtypes, missing required values and invalid resource inputs. Time-aware local resource labels are canonicalized to UTC; ambiguous naive local labels are rejected. Numeric CSV-style values are returned as numeric resources rather than strings.

The architecture joins the small, spatially aggregated hourly resource series before applying the existing rolling/event helpers globally. A 175,320-hour two-resource float64 table contains about **2.8 MB** of values, excluding index/processing overhead; gridded weather is processed one block at a time. This avoids introducing an incremental event-state algorithm that could split events or lose future window support at arbitrary file edges. A resumable production/checkpoint scheduler is not implemented by this helper.

### Real-data experiment

Reused the original January 2020 instant/accum/mask files, the existing wind/PV archived outputs, and the clean Python 3.11.11 terrain environment. No download, new package, credential or Mac-environment change was needed. Modeled all **695 selected cells** with unchanged cubic/uniform wind and fixed-tilt 35° PV. The continuous reference matches archived wind within **1.67e-16** and archived PV exactly.

Wrote/reopened temporary NetCDF pairs with identical decoded values, then removed them. Tested snapshot partitions **[0,500,744]** and **[0,1,25,169,481,743,744]**, the latter including one-record initial/final files. Both preserve **743 complete intervals**, with zero selected-cell GHI and temperature differences, zero PV differences, and maximum wind differences **4.34e-19** and **2.78e-17**. Numerical comparison tolerance was 1e-12. No physical model, threshold, mask or deployment assumption was changed.

Compared the strict hourly catalogue and nine 48-hour capacity-mix/threshold cases per partition: **18 rolling checks**. All diagnostics, timestamps, durations, qualifying-window counts and outer-boundary flags match the continuous baseline. Both retain 502 strict low hours, 31 periods and zero ≥24-hour periods under the existing PV reference definition.

### Failure controls and synthetic calendars

For the existing 75%-wind/0.06 scenario, global processing preserves **one 199-hour window-support union**. Deliberately detecting independently in each file creates **two event records** in both partition cases. The irregular case also counts only **186** union hours, losing **13 hours** of support. Therefore concatenating independent catalogues is not equivalent to detecting events from joined resource means.

Created explicitly synthetic 216-hour sequences with a 72-hour internal block at CF 0.01 surrounded by CF 0.5. New Year, leap-February and nonleap-February cases each preserve a 72-hour strict period and an 80-hour 48h-window support union with 33 qualifying windows. Naive independent monthly detection counts only **53 union hours** in each. These are algorithm fixtures, not observed generation events. Unit tests also preserve all 24 UTC hours of February 29 and correctly convert aware spring/fall Pacific DST labels without inventing UTC gaps/duplicates; the January-only CAISO importer was not generalized.

### Verification and records

Added [continuity helper](../scripts/continuous_resources.py), [reproduction driver](../scripts/18_verify_chunk_continuity.py), [13 continuity tests](../tests/test_continuous_resources.py) and the [method report](chunk_continuity.md). All **85 tests** passed. Independent handwritten wind calculations/archived PV regression and direct-slice window/union/run extraction verified all 18 real-data cases; all event times/durations/counts/censoring flags agree with the preserved prior baseline catalogue. Independent calculations reproduced the synthetic fixtures and naive failure controls. Source/output/code hashes and [verification](continuity_verification.json) are retained. All earlier scientific artifacts remain unchanged.

Saved three separate compact resource series, [weather comparisons](../results/tables/continuity_weather_checks_2020_01.csv), [window checks](../results/tables/continuity_event_checks_2020_01.csv), [hourly checks](../results/tables/continuity_hourly_reference_checks_2020_01.csv), [synthetic cases](../results/tables/continuity_synthetic_calendar_checks.csv), [synthetic event times](../results/tables/continuity_synthetic_events.csv), and [metadata](../results/tables/continuity_metadata_2020_01.json).

### Scope and next requirements

The proposed UTC 2005–2024 core has **175,320 complete hours**, including **120 hours on five leap days**, with end labels 2005-01-01 01:00 through 2025-01-01 00:00 UTC. It needs appropriate endpoint weather and outside-core window/event context; cropping also needs an explicit event-inclusion rule. This count is a calendar check, not processed climate data.

Actual contiguous multi-month data, source-convention/version changes, acquisition resumption and full-scale performance still need a rehearsal. Physical wind bias, asset lineage, PV amplitude, held-out-period validation and final event/temperature choices remain open in the updated [readiness record](expansion_readiness.md). The computational checks do not imply that the full historical study is validated or complete.

## November 24 fixed-layout decision, matched PV and expansion preparation

### Scope and confirmed decision

The author requested completing the remaining preparation before expanding to 2005–2024. The author selected a **fixed reference layout** with year-specific matched fleets for validation and requested its justification. Recorded the rationale in the [study protocol](study_protocol.md): expose the same renewable system to different years of weather so deployment growth, changed locations and equipment turnover do not confound weather comparisons. This supports a counterfactual resource-system study, not reconstructed historical production. A 2020 utility-scale reference is proposed; final physical models, complete PV weights and reference hashes remain conditional on validation.

### Matched fixed-tilt PV comparison

Reused the preserved December 2019/January 2020 monthly EIA inventories, annual EIA-860 2020 archive, previously verified EIA-923 PV-only extraction, original January ERA5 files and saved boundary. No raw files were redownloaded for this comparison. Source hashes and selected-generator/model/output records are retained in [run metadata](../results/tables/fixed_tilt_pv_validation_metadata_2020_01.json). Annual solar workbook: `3_3_Solar_Y2020.xlsx`, Operable and Retired and Canceled sheets, header Excel row 2; monthly Operating sheets use the same header row. EIA instructions establish AC nameplate versus separately reported DC capacity and orientation conventions.

Added [PV cohort helper](../scripts/january_pv.py) and [driver 19](../scripts/19_validate_fixed_tilt_pv.py). Require whole-plant monthly PV unit populations/status/capacity/service/fuel consistency, pre-January operation, valid coordinates, annual unit/AC-capacity agreement and a numeric physical-plant January SUN/PV energy observation. Any unit failure excludes the entire plant; no partial denominators or synthetic state/fuel increments. Preserve missing energy rather than zero filling.

There are **539 stable capacity-matched plants / 10,241.9 MW** before equipment filtering. The fixed-tilt subset retains **219 plants / 345 generators / 2,636.5 MW AC** with reported valid tilt, azimuth and DC capacity. Exclude whole plants with positive tracking/mixed/east–west/concentrator/other-solar flags or missing fixed-tilt classification. Blank competing select-all flags mean not selected, not independently verified absent. Year-end equipment properties are qualified January proxies. The [audit](../results/tables/jan2020_pv_matching_audit.csv) retains all exclusions.

Model each unit with its reported orientation/DC-to-AC ratio, nearest-grid radiation/temperature and plant-coordinate solar geometry. Preserve NOCT 45°C, DC coefficient −0.004/°C, 14% other losses and 96% inverter efficiency; no fitted parameters. The observed cohort produces **294,147.955 MWh**, nominal CF **0.149956**. Model support is **735 of 744 Pacific-month hours**; full-month CF bounds **0.185284–0.197380**, energy **363,444.231–387,172.731 MWh**. Even the lower bound exceeds observed energy by **23.56%**. Nine unavailable hours are bounded 0–1, not imputed. Three observed-zero plants totaling 3.5 MW remain in the comparison; zero reported energy is not missing data. Annual geometry, operational effects, losses and radiation assumptions require further investigation; no single cause or correction factor is inferred. The [figure](../results/figures/fixed_tilt_pv_validation_2020_01.png), plant bounds, parameter table and hourly series are retained. This does not validate tracker, thermal or distributed-PV populations.

### Limited real-weather adjoining/summer/held-out rehearsal

Investigated public ERA5 access options. Public ARCO metadata included native reduced-Gaussian data rather than the original regular grid, and the probed ECMWF ARCO endpoint required authorization. Those products were not substituted into the original model. A small public Open-Meteo ERA5 probe was compared with original January forcing before selecting the secondary source for a processing-only rehearsal.

Added [driver 20](../scripts/20_rehearse_public_weather.py): five preselected in-state 0.25° cells, nearest selection, explicit ERA5 model, UTC, m/s, `elevation=nan` to disable downscaling. Fifteen successful API responses total **565,358 raw JSON bytes**; URL/SHA receipts, units, exact grid/time coverage and finite values are checked. Reconstruct rounded speed/direction components and convert preceding-hour radiation mean to energy solely for this labeled secondary-source experiment. Preserve attribution to ECMWF/Copernicus ERA5 and Open-Meteo, CC BY 4.0. Raw API/cache/NetCDF files remain outside Git.

January overlap at all five cells totals 744 records each; largest absolute differences are **0.06918 m/s**, **0.07499°C**, **0.49781 W/m²**. Small differences and upstream version limits mean this source must not be called identical to, or silently spliced with, original CDS forcing. [Overlap table](../results/tables/public_weather_overlap_2020_01.csv) and [requests/metadata](../results/tables/public_weather_rehearsal_metadata.json) preserve the evidence.

With unchanged cubic wind/PV35 parameters and five-cell cosine-latitude weights, processed **1,440 complete hours for January–February 2020**, **744 for July 2020**, **744 for January 2021**. Monthly files, including true leap-month boundaries and endpoint-only final files, reproduce continuous resource results with **zero difference**. Canonicalizing API microseconds/NetCDF nanoseconds resolves an initial catalogue dtype-comparison failure without changing timestamps or model values. Strict and 48-hour catalogues match as well. All three selected limited cases have zero ≥24h strict episodes and zero qualifying 48h/6% windows; these are five-cell computational outcomes, not statewide event frequencies. Verified offline replay uses **zero weather downloads**. No parameters were selected using the summer or held-out means. No additional-period matched generation validation is claimed.

### Protocol, temperature and acquisition checks

Recorded the core calendar, outside-core context, episode-onset versus exposure rules, censoring, existing hourly/window definitions, capacity-share/threshold sensitivities and trial deficit units in the [protocol](study_protocol.md). Preserved the difference between resource availability, net generation and unserved demand. The confirmed fixed-layout concept is separate from unresolved physical/reference-inventory choices.

Added [temperature helpers](../scripts/temperature_extremes.py): complete UTC daily means of end-labeled hourly interval temperatures, flagging incomplete edge days and rejecting interior gaps; leave-one-year-out 5/95% seasonal percentiles on a circular ±15-day 365-day calendar; February 29 interpolation; at least 18 complete other baseline years; sustained three-day strict hot/cold runs with censoring. Synthetic tests check leap support, independent-year fitting and refusal to estimate a climatology from the January pilot. This is an implemented working definition of statewide background temperature, not local Tmax, demand or a calculated real climatology. Final coincidence/uncertainty estimators still need implementation and final inputs.

Added [acquisition/preflight helper](../scripts/archive_preflight.py) and [driver 21](../scripts/21_prepare_archive_plan.py). Generated **242 calendar-valid monthly request plans**: 240 core months plus December 2004/January 2025 context. Core hours sum to **175,320**. Plan status is explicitly `PLAN_ONLY_NOT_SUBMITTED`; no client retrieval occurs. Original January data pass [QC](../results/tables/archive_preflight_january_2020.json) for expected grids, complete support, variables/dimensions/units/step type, wind vector convention, final ERA5 expver=1, finite values and broad physical/sentinel bounds. Receipt tests verify request hash, byte hash/length and completion status; missing/partial/tampered/different-request entries fail. A complete production scheduler and limited direct-CDS restart/performance exercise remain open. Presence-only inspection found neither `CDSAPI_KEY` nor a default `.cdsapirc` in this cloud environment; no secret contents were inspected or disclosed.

### Verification, automation and remaining gates

Added **17 scientific/input tests**, for a total of **102 passing tests**, using the preserved Python 3.11.11 terrain environment and pinned dependency set. [Independent driver 22](../scripts/22_verify_pre_expansion.py) directly checks raw monthly/annual unit populations, technology, AC capacities and original EIA-923 energy. Manual aggregation verifies cohort CF and nine-hour energy bounds. Direct pvlib equations/cubic calculations, without importing the new project helpers, reproduce every value of all three five-cell resource series within **2.23e-16**; direct run/window checks agree. [Independent results](../results/tables/pre_expansion_independent_checks.json) and [overall verification](pre_expansion_verification.json) retain scope/checksums. The PV figure was inspected. Earlier scientific outputs are preserved.

Added a [GitHub Actions workflow](../.github/workflows/scientific-checks.yml) for source syntax and computational tests on main pushes/pull requests, using Python 3.11.11 and `requirements-terrain.txt`. It runs without raw-data downloads or CDS credentials. The first remote run, [45484953091](https://github.com/Giulian14/California_Dunkelflaute/actions/runs/45484953091), failed during setup because `ubuntu-latest` resolved to Ubuntu 26.04 without a Python 3.11.11 build; no scientific test ran. Verified the official actions/python-versions manifest and pinned Ubuntu 24.04, which has the exact interpreter build. Remote execution status is checked separately from local success; do not conflate those.

Updated README, [latest evidence report](pre_expansion_checks.md), [protocol](study_protocol.md) and [readiness](expansion_readiness.md). Full-period expansion has **not** started. Remaining scientific gates are explicit: explain/quantify wind underprediction and fixed-tilt PV overprediction with independent physical/site evidence; implement/validate tracker/reference-fleet treatment; validate fixed parameters against matched populations in an unused season/year; run a limited source-consistent full-grid CDS rehearsal; freeze final reference/model hashes. The five-cell exercise closes a limited processing question, not those gates. Further progress needs the corresponding weather/site information and a configured private CDS client, rather than another confirmation of the author's fixed-layout decision.

## How to use this record for the paper

Use the linked source and algorithm records to write a reproducible methods narrative. Summarize the original proxy as a pilot, then explain the selected final physical models and event definitions. Keep alternative scenarios in a sensitivity subsection. Put environment troubleshooting and detailed execution history in a reproducibility appendix rather than presenting each interactive-console action as a scientific method.

Before final writing, check every reported number against the matching scenario, interval support, denominator, source version and verification record. Preserve the distinction between modeled energy availability, actual generation, climatological rarity and electricity adequacy.
