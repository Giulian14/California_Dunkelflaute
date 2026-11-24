# January 2020 pilot outputs

The six original PNG figures and two original CSV tables are preserved unchanged from the author's uploaded `results.zip`. They describe preliminary resource models, not a completed 2005–2024 Dunkelflaute analysis.

## Figures

| Figure | Generating script | Type |
| --- | --- | --- |
| [California grid mask](figures/california_era5_grid_mask.png) | `02b_build_california_mask.py` | Map |
| [Bounding-box weather averages](figures/era5_bounding_box_january_2020.png) | `02_inspect_era5.py` | Time series |
| [California administrative-area weather averages](figures/era5_california_january_2020.png) | `03_california_averages.py` | Time series |
| [Illustrative wind capacity factor](figures/illustrative_wind_cf_2020_01.png) | `04_wind_capacity_factor.py` | Time series |
| [Solar resource proxy](figures/solar_resource_proxy_2020_01.png) | `05_solar_resource_proxy.py` | Time series |
| [Low-resource duration distribution](figures/trial_low_resource_duration_histogram_2020_01.png) | `06_detect_trial_periods.py` | Histogram |

The figures cover three distinct types: maps, time series, and histograms. All time-series labels use UTC.

## Tables

- [Trial low-resource periods](tables/trial_low_resource_periods_2020_01.csv): 31 observed periods, of which 30 are fully observed. Durations total 545 hours, and the longest observed duration is 19 hours. `start_utc` and `end_utc` delimit the covered intervals; duration is `(end_utc - start_utc)` in hours. The first period touches the data boundary, so its observed 17-hour duration is a lower bound.
- [Minimum-duration sensitivity](tables/trial_duration_sensitivity_2020_01.csv): counts periods meeting each minimum duration, both including boundary-touching periods and restricting to fully observed periods. No observed period reaches 24 or 48 hours.

## Interpretation and review

The trial condition is illustrative wind capacity factor < 0.20 AND solar resource proxy < 0.20, with conversion before spatial averaging. The spatial mask includes state waters. Resource weighting assumes uniform capacity per unit area rather than actual generation sites. Solar is normalized horizontal irradiance, not a full photovoltaic generation model. Many low-resource hours arise during ordinary nighttime conditions.

During repository review, all PNG files passed image-integrity checks and were visually inspected. CSV durations were checked against their timestamps, periods were checked for ordering and overlap, and sensitivity counts were recomputed from the catalogue. After the processed CSVs were supplied, alignment and detection were rerun using those actual saved values. Both regenerated result tables matched these tables exactly. This verifies the saved-series-to-results stage, in addition to internal consistency. After the raw ERA5 inputs were supplied, the [full workflow was independently reproduced](../docs/full_workflow_verification.md) in a clean Python 3.11.11 environment with the pinned direct dependencies. Both final result tables still match exactly. All six figures regenerated successfully; original uploaded images are retained here without a claim of pixel-equivalent rendering across operating systems. See the [processed-data verification notes](../data/processed/README.md).

Original-file byte sizes, image dimensions, and SHA-256 checksums are recorded in [the results manifest](../docs/results_manifest.json).

## PV model extension

The additional `pv_ac_capacity_factor_2020_01.png` figure compares modeled fixed-tilt AC CF with the GHI reference. Separate `tilt25` and `tilt45` plots show sensitivity scenarios. These curves have different physical denominators; their separation is not an accuracy score.

`pv_model_metadata_*.json` files record assumptions, input hashes, timestamp conventions, runtime versions, and low-sun diagnostics. `pv_model_summary_*.csv` files contain scenario summaries. [The tilt sensitivity table](tables/pv_tilt_sensitivity_2020_01.csv) collates the three summaries. See [the model documentation](../docs/pv_model.md) and [verification record](../docs/pv_model_verification.json). Original proxy-based event catalogues are unchanged.

## Modeled-PV event-definition comparison

[The comparison figure](figures/wind_pv_event_comparison_2020_01.png) shows individual CFs, 48-hour combined means for three capacity mixes, and sensitivity of merged events/covered hours. The hourly reference catalogues are in `pv_reference_*.csv`; window-based results are in `wind_pv_48h_*.csv`. Their distinct meanings, edge-context flags, input provenance, and verification are documented in [the comparison report](../docs/event_comparison.md).

The 35° PV baseline gives zero observed 24-hour uninterrupted events and zero low 48-hour windows for a 50/50 rated-capacity mix at threshold 0.06. Other hypothetical mixes/thresholds produce periods, including one 199-hour union period for 75% wind at 0.06. Original pilot and PV artifacts are preserved.

## Wind curve and geographic weighting assessment

[The four-panel assessment figure](figures/wind_model_geography_assessment_2020_01.png) separates curve and location assumptions. `wind_assessment_summary_2020_01.csv` reports the eight wind scenarios; `wind_assessment_event_sensitivity_2020_01.csv` contains 72 capacity-mix/threshold cases. Other `wind_assessment_*` tables preserve reference periods, merged-window catalogues, plant-to-grid assignments, normalized grid weights, and run metadata.

The [assessment method](../docs/wind_assessment.md), [verification record](../docs/wind_assessment_verification.json), and [dated research log](../docs/research_log.md) describe the evidence and limits. All original pilot, PV, and event-comparison results remain separate.

## Observed-generation shape benchmark

The [figure](figures/observed_generation_shapes_2020_01.png), [nine-scenario metrics](tables/observed_shape_metrics_2020_01.csv), [30 complete local daily means](tables/observed_shape_daily_means_2020_01.csv), and [EIA scope summary](tables/eia923_generation_scope_summary_2020_01.csv) document the first production comparison. The [observation metadata](tables/generation_observation_metadata_2020_01.json) and [comparison metadata](tables/observed_shape_comparison_metadata_2020_01.json) retain source hashes, Pacific-time assumptions, exclusions and normalization definitions. Read the [method](../docs/observed_generation_comparison.md) before interpreting correlation or dimensionless shape error as physical accuracy; this is not amplitude/event validation.

## January plant matching and energy bounds

[Inventory summary](tables/january_wind_inventory_summary_2020_01.csv), [matched cohort bounds](tables/matched_january_wind_bounds_2020_01.csv), [424 plant/curve bounds](tables/matched_january_wind_plant_bounds_2020_01.csv), [site assignments](tables/matched_january_wind_site_assignments_2020_01.csv), and [figure](figures/matched_january_wind_bounds_2020_01.png) show a material reference-model energy shortfall. Bounds cover nine missing hours under CF 0–1, not all model uncertainty. [Run metadata](tables/matched_january_wind_metadata_2020_01.json) records assumptions and input/output hashes. The [monthly operational/plant source audit](tables/generation_source_monthly_audit_2020_01.csv), [hourly metrics](tables/generation_source_hourly_metrics_2020_01.csv) and [API metadata](tables/generation_source_audit_metadata_2020_01.json) retain the unresolved EIA/CAISO differences. Read the [interpretation](../docs/january_wind_match.md) before using any result as historical climate evidence.

## Wind-site and capacity-consistency follow-up

The [eight sampling/curve bounds](tables/wind_site_sampling_bounds_2020_01.csv), [106-site coordinate audit](tables/wind_site_coordinate_audit_2020_01.csv), [206 IEC II plant/sampling diagnostics](tables/wind_site_iec2_diagnostics_2020_01.csv), [figure](figures/wind_site_sampling_bounds_2020_01.png), and [metadata](tables/wind_site_diagnostic_metadata_2020_01.json) use or document the refined 103-plant subset. Read the [capacity qualification](../docs/wind_site_diagnostics.md) before using the older 106-plant result. Neither source-coordinate agreement nor bilinear interpolation establishes terrain/micrositing accuracy.

## Terrain reference and curve availability

[Terrain site values](tables/wind_terrain_site_audit_2020_01.csv), [terrain figure](figures/wind_terrain_comparison_2020_01.png) and [source/unit metadata](tables/wind_terrain_metadata_2020_01.json) compare approximate point/grid elevations on different support and vertical references. [Model candidate coverage](tables/turbine_curve_candidate_coverage_2020_01.csv), [generator flags](tables/turbine_curve_candidate_generators_2020_01.csv) and [curve provenance](tables/turbine_curve_coverage_metadata_2020_01.json) distinguish theoretical exact-name candidates from validated manufacturer curves. Read [interpretation](../docs/wind_terrain_and_curve_audit.md); neither audit changes modeled output or establishes wind-bias causation. Contains modified Copernicus Climate Change Service information (2026). Neither the European Commission nor ECMWF is responsible for use of the Copernicus information or data.

## File and calendar continuity

[Weather checks](tables/continuity_weather_checks_2020_01.csv), [18 window checks](tables/continuity_event_checks_2020_01.csv), [hourly reference checks](tables/continuity_hourly_reference_checks_2020_01.csv), and [run metadata](tables/continuity_metadata_2020_01.json) compare two/six file partitions with continuous January processing. [Synthetic calendar checks](tables/continuity_synthetic_calendar_checks.csv) and [explicitly synthetic event times](tables/continuity_synthetic_events.csv) cover New Year/leap/nonleap boundaries. Per-file detection is included as a deliberate failure control. Read the [scope and limits](../docs/chunk_continuity.md); this is computational evidence and does not close the physical wind/PV validation gaps.
## November 24 additional validation and preparation

The [fixed-tilt PV comparison and weather rehearsal report](../docs/pre_expansion_checks.md) documents `fixed_tilt_pv_*`, `jan2020_pv_matching_audit.csv`, `public_weather_*`, and `rehearsal_*_five_cells.csv` outputs. These are separate scenarios; earlier pilot results are preserved. The new PV figure includes missing-hour bounds. Rehearsal weather derives from ECMWF/Copernicus ERA5 processed by Open-Meteo ([CC BY 4.0](https://open-meteo.com/en/licence)); attribution and transformations are retained in the report/metadata.

`era5_2005_2024_request_plan.json` is an **unsubmitted** calendar/request plan, not downloaded weather or a climate result. `archive_preflight_january_2020.json` and `pre_expansion_independent_checks.json` record input/computational verification. See the [study protocol](../docs/study_protocol.md), [overall verification](../docs/pre_expansion_verification.json) and [research log](../docs/research_log.md) for meaning, limits and remaining gates.
