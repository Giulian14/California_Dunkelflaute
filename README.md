# California Dunkelflaute Research

Graduate project for EN 530.637 — Energy Meteorology, Johns Hopkins University.

The [dated research log](docs/research_log.md) records the workflow, decisions, checks, results and limitations needed for later methods writing. Earlier history is explicitly marked as reconstructed.

## Research question

How frequently do prolonged periods of low wind and solar energy availability occur in California, and how often do they coincide with temperature extremes?

The intended study period is **2005–2024**. Current work is a **January 2020 pilot**, not a completed climatological analysis.

## Current status

The pilot workflow has been run successfully on the author's Mac using Python 3.11, Anaconda, and Spyder. It opens existing ERA5 files, builds a California mask, calculates weather averages, estimates preliminary resource indicators, and detects trial low-resource periods.

**The eight uploaded Python scripts are now in `scripts/`, preserved unchanged from the author's archive.** The exact California boundary file is included in `data/boundaries/`, with [source and checksum documentation](docs/boundary_provenance.md). The [six pilot figures and two result tables](results/README.md) are also included, with file checksums and review notes. The reported Python 3.11.11 package versions are recorded in [`requirements.txt`](requirements.txt), with [environment setup and verification notes](docs/environment.md). This is a direct-dependency snapshot, not a complete environment lockfile.

All eight scripts passed syntax checks. Synthetic-data checks passed for hourly alignment, empty detections, a 30-hour internal period, start/end boundary flags, an all-low window, and rejection of missing timestamps. The [saved processed CSVs](data/processed/README.md) are now included. Rerunning alignment and detection from those inputs reproduced both final result tables exactly, including 545 low-resource hours, 31 periods, and 30 fully observed periods. The [full January workflow has now also been independently reproduced](docs/full_workflow_verification.md) from the supplied raw ERA5 inputs in a clean Python 3.11.11 Linux environment with the seven pinned package versions. The mask matches exactly; weather and solar series agree to numerical precision; wind CF differs by at most 1.73e-9, with zero changed threshold classifications. Both final result tables match exactly. Original outputs are preserved, and raw NetCDF files remain excluded from Git.

## Data

- [ERA5 hourly data on single levels](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels), Copernicus Climate Data Store.
- January 1–31, 2020, hourly, in UTC.
- Bounding box: north 42°, west −125°, south 32°, east −114°.
- Variables: 100 m wind components (`u100`, `v100`), 2 m temperature (`t2m`), and surface solar radiation downwards (`ssrd`).
- Grid: 41 latitudes × 45 longitudes, with 744 hourly timestamps.
- California boundary: U.S. Census Bureau TIGERweb, 2026 vintage, selected using GEOID 06 and exported in longitude/latitude coordinates.

The existing download was a ZIP archive despite its .nc filename. Its extracted files are:

```text
data_stream-oper_stepType-instant.nc
data_stream-oper_stepType-accum.nc
```

The administrative mask selects **695 grid centers** inside or on California's boundary. It includes state waters and is not a land-only mask.

Raw NetCDF files and credentials are excluded from Git. No additional ERA5 download is needed to rerun the pilot on the existing local data.

## Preliminary methods

1. Wind speed: sqrt(u100² + v100²), in m/s.
2. Temperature: t2m − 273.15, in °C.
3. For this hourly CDS ERA5 product, ssrd / 3600 gives preceding-hour mean irradiance in W/m².
4. Spatial averages use cosine-of-latitude area weights.
5. Illustrative wind capacity factors use a cubic curve between cut-in at 3 m/s and rated output at 12 m/s, full output below cut-out at 25 m/s, and zero outside the operating range.
6. The solar resource proxy is irradiance / 1000 W/m², clipped to 0–1. It is **not a full photovoltaic capacity-factor model**.
7. Resource conversion occurs at each grid cell before spatial averaging, representing hypothetical capacity distributed uniformly per unit area within the mask.
8. Adjacent instantaneous wind capacity factors are averaged to approximate preceding-hour values. This assumes linear changes between snapshots; it is not an observed hourly generation average.
9. The first interval lacks the preceding wind snapshot and is excluded, leaving **743 hourly intervals**.
10. Trial low-resource periods require both normalized values to be strictly below 0.20. Minimum-duration sensitivity is evaluated at 6, 12, 18, 24, and 48 hours. Periods touching data boundaries are flagged.

## Pilot results

| Metric | January 2020 |
| --- | ---: |
| Illustrative wind capacity factor, monthly mean over 744 snapshots | 0.047 |
| Solar resource proxy, monthly mean over 744 hours | 0.116 |
| Hours meeting both trial thresholds | 545 of 743 |
| Observed uninterrupted low-resource periods | 31 |
| Fully observed periods | 30 |
| Longest observed low-resource duration | 19 hours |
| Observed periods reaching 24 hours | 0 |

One period touches the start of the available intervals. Its observed 17-hour duration is a lower bound; its full duration is unknown. Most observed periods last 17–18 hours, suggesting a strong influence from the day–night cycle.

**These results do not establish California's Dunkelflaute frequency or the absence of longer events outside the observed window.**

## PV generation extension

A separate [fixed-tilt PV model](docs/pv_model.md) now estimates AC capacity factor using pvlib, panel orientation, temperature, system losses, and inverter clipping. It was tested on the existing January ERA5 inputs across all 695 selected cells and 743 complete intervals, with 10 automated tests passing.

The representative 35° south-facing scenario averages **0.169478 AC capacity factor** over those intervals. Tilt scenarios at 25° and 45° average 0.158541 and 0.176466. These are modeled system scenarios, not validated California fleet output. The original GHI proxy and event tables remain unchanged. A separate [event-definition comparison](docs/event_comparison.md) now uses modeled PV, including 27 rolling-window sensitivity cases.

Install the optional extension dependencies and run from the repository root:

```bash
python -m pip install -r requirements-pv.txt
python -m unittest discover -s tests -p 'test_pv_model.py' -v
python scripts/07_pv_capacity_factor.py --headless
```

The model requires the existing raw inputs and mask. [Model assumptions and results](docs/pv_model.md), [PV figure](results/figures/pv_ac_capacity_factor_2020_01.png), and [tilt sensitivity table](results/tables/pv_tilt_sensitivity_2020_01.csv) are included. Raw NetCDF files remain excluded.

## Event-definition comparison using modeled PV

The new [comparison](docs/event_comparison.md) uses the included processed series and PV metadata. The 35° PV baseline has **502 simultaneous low hours**, versus 545 with the old irradiance proxy; neither has an observed 24-hour uninterrupted event. For a hypothetical **50/50 rated-capacity mix**, the minimum 48-hour combined CF is **7.12%**, above the 6% comparison threshold, giving zero qualifying windows.

Results depend on the portfolio and definition: at 75% wind rated capacity and a 6% threshold, qualifying windows merge into one **199-hour union period**. This does not mean generation is below 6% in every hour, or that every possible 48-hour mean within the union is below 6%. The comparison includes tilt, mix, and threshold sensitivity and conservatively flags uncertain edge context.

```bash
python scripts/08_compare_event_definitions.py --headless
```

This step needs no raw ERA5 data or additional downloads. All **22 tests** passed, and independent direct-slice/support checks agreed for all 27 rolling-window cases. See the [comparison figure](results/figures/wind_pv_event_comparison_2020_01.png), [sensitivity table](results/tables/wind_pv_48h_sensitivity_2020_01.csv), and [method and limits](docs/event_comparison.md). This remains a January scenario study, not a multi-year climatology or actual fleet adequacy assessment.

## Wind curve and geographic weighting assessment

The [November 23 assessment](docs/wind_assessment.md) compares the original cubic curve and three published 100 m WTK onshore reference curves, each with uniform-area and fixed EIA-860 2020 capacity-location weights. The reference inventory retains **117 operating generator records at 101 plants, totaling 5,916.5 MW**, mapped to 25 ERA5 centers. It is a fixed end-2020 layout, not January hourly fleet availability.

Across 743 intervals, mean modeled wind CF ranges from **4.73% to 12.56%**. The IEC II curve with capacity-location weights gives **9.92%**, versus **4.73%** for cubic/uniform. All eight cases retain zero observed baseline events at the 24-hour simultaneous definition and the 50/50, 0.06 combined definition. Other mixes and thresholds remain sensitive to these choices. Higher CF is not evidence of higher accuracy without observational validation.

```bash
python scripts/09_assess_wind_model.py --headless
```

The small reference datasets and source/license records are committed; existing ERA5 wind and mask inputs are still needed locally. [The method](docs/wind_assessment.md), [summary](results/tables/wind_assessment_summary_2020_01.csv), [figure](results/figures/wind_model_geography_assessment_2020_01.png) and [verification](docs/wind_assessment_verification.json) record the controlled design. All **33 tests** passed, with independent checks of capacity selection, weights, published-curve outputs, eight hourly cases and 72 event sensitivities.

## First observed-generation benchmark

The [November 23 comparison](docs/observed_generation_comparison.md) uses official CAISO five-minute production and EIA-923 monthly records. It aligns **735 shared hours** and **30 complete Pacific days**. With the same cubic curve, capacity-location weighting increases hourly wind correlation from **0.341 to 0.783**; IEC II/location gives **0.796**. PV correlation is **0.969 hourly** but **0.641 across daily means**, emphasizing the role of the shared day–night cycle.

These are temporal-shape diagnostics across unmatched populations, **not CF-amplitude or event validation**. EIA and CAISO totals are not reconciled; source frequency, missing values, synthetic state increments, curtailments and time assumptions are documented. All **42 tests** passed, with independent Excel/array checks. The [metrics](results/tables/observed_shape_metrics_2020_01.csv), [figure](results/figures/observed_generation_shapes_2020_01.png), [source metadata](results/tables/generation_observation_metadata_2020_01.json) and [verification](docs/observed_generation_verification.json) are committed. Reproduce using the included processed data:

```bash
python scripts/11_compare_observed_shapes.py --headless
```

## Initial January wind diagnostic (qualified by follow-up)

The [annual-capacity follow-up](docs/wind_site_diagnostics.md) subsequently identified three ambiguous plants; the more conservative subset has 103 plants and observed nominal CF 16.92%. The initial results below remain conditional on the monthly-snapshot match.

The [January inventory match](docs/january_wind_match.md) retains **106 plants / 123 generators / 5,985.7 MW**, covering **99.6%** of EIA's California January wind energy. Its observed nominal monthly CF is **17.06%**. The IEC II reference model's full-month CF is bounded at **9.83%–11.04%**, even allowing every missing hour full output. All four reference curves fall below observed energy under these matching assumptions. The earlier shape agreement therefore does not establish energy-amplitude accuracy; investigate wind representation and turbine/hub assumptions before expanding the climatology.

The [bounds](results/tables/matched_january_wind_bounds_2020_01.csv), [figure](results/figures/matched_january_wind_bounds_2020_01.png), [inventory decisions](data/reference/jan2020_wind_plant_audit.csv) and [verification](docs/january_wind_verification.json) preserve the evidence. Missing-hour bounds are not total model-error confidence intervals. An additional [EIA-930/CAISO/EIA-923 source audit](results/tables/generation_source_monthly_audit_2020_01.csv) leaves their population discrepancy explicitly unresolved. All **56 tests** passed; earlier scenario files and event counts remain unchanged.

```bash
python scripts/13_bound_matched_wind_generation.py --headless
```

## Latest wind-site checks and expansion readiness

The [site audit](docs/wind_site_diagnostics.md) excludes whole plants with monthly/annual capacity disagreement, leaving **103 plants / 119 generators / 5,842.1 MW**. Observed nominal monthly CF is **16.92%**; IEC II bounds are **9.85%–11.06% nearest-center** and **8.68%–9.89% bilinear-vector** sampling. Source coordinates agree within four metres, but neither interpolation resolves the energy shortfall. Annual reported hub heights and predominant equipment remain descriptive; terrain and actual January turbine identities need further validation.

The [expansion-readiness record](docs/expansion_readiness.md) lists the remaining physical, PV, temporal-boundary, fleet-definition and event-analysis checks before 2005–2024 production processing. All **63 tests** passed, with independent checks of the subset, eight sampling/curve series and 206 IEC II plant/sampling cases. Earlier numerical artifacts are preserved and their qualifications are explicit.

## Terrain and curve-provenance audit

The [latest audit](docs/wind_terrain_and_curve_audit.md) compares public ERA5 terrain fields with **103 USGS DEM point elevations**. Median absolute point/grid height difference is **205 m** across **24 shared weather centers**. This adds terrain context, but some high wind residuals occur where elevations closely agree; no terrain-based wind correction is justified.

The pinned turbine archive has exact-name candidates for only **248.4 MW / 4.25%** of the subset, and those two specifications are theoretical without linked primary references. Manufacturer-specific curve validation and independent hub-height wind information remain open. All **72 tests** passed, including independent terrain/candidate checks and replay of **110 cached source files with zero downloads**. The [research log](docs/research_log.md) and [readiness record](docs/expansion_readiness.md) track the remaining work.

The current complete suite requires the terrain extension; this includes all earlier runtime dependencies:

```bash
python -m pip install -r requirements-terrain.txt
python -m unittest discover -s tests -v
```

ERA5-derived outputs contain modified Copernicus Climate Change Service information (2026). Neither the European Commission nor ECMWF is responsible for any use of the Copernicus information or data. USGS 3DEP/EPQS supplies the DEM point reference; source licenses and attribution are retained.

## Continuous-file processing verification

The [November 24 continuity check](docs/chunk_continuity.md) carries one weather bracket across files and joins compact resource means before global event detection. Repartitioning January into **two and six NetCDF file pairs** preserves all **743 complete hours**, all 695-cell forcings and the existing wind/PV results to numerical precision. All **18** rolling-window comparisons match, including event timestamps, durations and boundary flags.

A deliberately incorrect per-file control splits the existing **199-hour** union into two records; irregular files also lose **13 covered hours**. Synthetic New Year/leap/nonleap controls preserve 72-hour strict periods and 80-hour window unions, while naive independent monthly processing counts only 53 union hours. These fixtures are algorithm checks, not observed events. All **85 tests** passed; [run metadata](results/tables/continuity_metadata_2020_01.json), [comparisons](results/tables/continuity_weather_checks_2020_01.csv), [independent verification](docs/continuity_verification.json) and the [research log](docs/research_log.md) record the evidence.

Real adjacent-month inputs, production acquisition/resumption and physical-model validation remain necessary. This stage does not establish a 20-year climatology.

## Local workflow

To reproduce the event tables directly from the included processed series, run from the repository root:

```bash
python scripts/05b_align_hourly_resources.py
python scripts/06_detect_trial_periods.py
```

These two steps do not require raw ERA5 files or API credentials. See the [processed-data notes](data/processed/README.md) for units, verification scope, and the legacy sensitivity diagnostic.

For the full workflow using existing raw ERA5 inputs:

Skip `01_download_era5.py` when using the existing data. It is retained as the original request record, contains a Mac-specific output path, and starts a CDS request when executed or imported. It does not extract the ZIP response. The analysis scripts use paths relative to the project directory.

Run scripts in this order once the input files are available locally:

```text
scripts/02_inspect_era5.py
scripts/02b_build_california_mask.py
scripts/03_california_averages.py
scripts/04_wind_capacity_factor.py
scripts/05_solar_resource_proxy.py
scripts/05b_align_hourly_resources.py
scripts/06_detect_trial_periods.py
```

Inputs belong in `data/raw/`, with the saved Census GeoJSON in `data/boundaries/`. Derived files go to `data/processed/`; figures and tables go to `results/figures/` and `results/tables/`.

The local workflow produces maps, time series, and a duration histogram.

## Remaining work

- Investigate the plant-matched wind energy shortfall, validate PV amplitudes, and justify final deployment/physical assumptions before a multi-year run.
- Extend and verify event extraction across contiguous months and years, with adequate boundary context.
- Assess land/coastal-mask assumptions and PV capacity-location weighting; wind-location sensitivity is now documented.
- Establish a final event definition that accounts for ordinary nighttime conditions, seasonality, and model uncertainty.
- Extend the validated workflow to 2005–2024.
- Analyze temperature extremes, meteorological mechanisms, and threshold sensitivity.

Temperature is a demand proxy. Actual load and electricity-system data would be needed to quantify electricity shortfalls; a meteorological renewable-energy drought is not automatically an electricity shortage.
