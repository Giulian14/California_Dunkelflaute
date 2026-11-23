# Terrain reference and turbine-curve provenance audit

The November 23, 2026 follow-up adds an independent DEM point reference and ERA5 terrain context at the existing 103 plant locations. It also checks what the pinned turbine archive can actually support. Neither check changes wind output, applies a terrain correction, or closes the wind-model validation gap.

## Sources and acquisition

Used the public [WeatherBench 2 ERA5 archive](https://weatherbench2.readthedocs.io/en/latest/data-guide.html), specifically `1959-2023_01_10-wb13-6h-1440x721_with_derived_variables.zarr`. Retrieved only its metadata, latitude/longitude arrays, surface geopotential, standard deviation of orography, and land–sea fraction. These are static fields, not a replacement six-hourly wind record. Five compressed single-chunk objects totaled **4,826,687 bytes**. The [source manifest](../data/reference/terrain/source_manifest.json) records URLs, hashes, Google object generations and retrieval date; original binary chunks remain outside Git.

For each plant coordinate, requested a point elevation from [USGS EPQS](https://epqs.nationalmap.gov/v1/docs) with `units=Meters`, `wkid=4326`, and acquisition-date metadata enabled. All **103** responses passed coordinate identity and finite/non-NoData checks. Preserve reported raster IDs, resolution values and acquisition dates; pixel resolution is not a claim of elevation accuracy. These are interpolated [3DEP DEM elevations](https://www.usgs.gov/faqs/how-accurate-are-elevations-generated-elevation-point-query-service-national-map), not surveyed turbine elevations.

Matched the static fields to the already selected wind-grid centers **exactly**. Convert western longitudes to the archive's 0–360 convention; reject a mismatched grid rather than silently interpolating it. Check field dimensions, units, codec, shape and byte counts. ERA5 geopotential `z` is converted to geopotential height by dividing by **9.80665 m/s²**. The USGS point and ERA5 grid values have different spatial support and vertical definitions; their difference is contextual, not a rigorous vertical-datum transformation or a direct model-error measurement.

The redistribution [license](../data/reference/terrain/LICENSE_COPERNICUS.txt) and [static metadata](../data/reference/terrain/static_field_metadata.json) are included. **Contains modified Copernicus Climate Change Service information (2026). Neither the European Commission nor ECMWF is responsible for any use of the Copernicus information or data.** USGS 3DEP/EPQS supplies the point DEM reference.

## Terrain findings

The 103 plants share **24 distinct weather centers**. Across plant points, signed USGS-minus-grid height has median **−35.81 m**, while the median absolute difference is **205.23 m**. Differences range from **−936.06 m to +517.30 m**. The sampled ERA5 orography standard deviation ranges from **49.32 m to 403.48 m**, and grid land fraction from approximately **0.900 to 1.000**.

These figures show substantial point/grid terrain differences, but do not establish that a height offset causes the wind shortfall. For example:

| Site | USGS point elevation | Nearest-grid geopotential height | Point minus grid | Observed CF minus IEC II upper-bound CF |
| --- | ---: | ---: | ---: | ---: |
| Voyager Wind II | 1,177.23 m | 1,028.53 m | +148.70 m | +0.260 |
| Tule Wind | 1,105.60 m | 821.78 m | +283.82 m | +0.225 |
| Shiloh I | 47.36 m | 44.22 m | +3.14 m | +0.130 |
| Shiloh 2 | 52.21 m | 33.78 m | +18.43 m | +0.125 |

Some large residuals occur despite similar point/grid elevations. Complex flow, roughness, turbine specifications, plant-point representativeness and reporting differences remain possible contributors. A plant coordinate is not a complete wind-farm footprint; matching elevation does not establish correctly modeled ridge/pass flow. No wind-speed scaling, height shift, fitted regression or statistical significance claim is made. Repeated weather cells and correlated plants preclude treating all 103 markers as independent weather samples.

See the [site table](../results/tables/wind_terrain_site_audit_2020_01.csv), [figure](../results/figures/wind_terrain_comparison_2020_01.png) and [terrain metadata](../results/tables/wind_terrain_metadata_2020_01.json). This is independent terrain context, **not an independent hub-height wind observation**.

## Turbine curve availability and provenance

Audited the same [turbine-models archive](https://github.com/NatLabRockies/turbine-models), pinned to commit `e9e4ccc6a87f50c0c65d236154a2897e752c47c9`. The EIA subset contains **49 reported manufacturer/model groups**, 119 generators and 5,842.1 MW. Two exact-name candidate mappings were identified conservatively:

- Vestas V47-660 → `Onshore/VestasV47_660kW_47`.
- Vestas V27-225 → `Distributed/VestasV27_225kW_27`.

These account for **248.4 MW / 4.2519%** of subset capacity. Whole plants whose generators all have those candidates account for **226.9 MW**. Both pinned specification files call their curves **theoretical** and provide empty primary-reference lists. They therefore do not establish manufacturer-validated January turbine behavior, despite name/rating agreement. The V27 candidate's archive group is Distributed. Do not extend either curve to larger models, conflate V90-1.8 with V90-3.0, or assign the DOE GE research reference to GE commercial models solely from rating or rotor diameter.

V90-3.0 alone accounts for **1,365 MW**, but no documented commercial V90 curve was accepted in this audit. Three manufacturer-document archive links returned HTTP 403; their search snippets and inaccessible tables were not used as numerical inputs. The [provenance metadata](../results/tables/turbine_curve_coverage_metadata_2020_01.json) records those URLs and qualifications. The absence of a candidate here does not imply that no suitable curve exists elsewhere.

See [capacity by model](../results/tables/turbine_curve_candidate_coverage_2020_01.csv), [generator flags](../results/tables/turbine_curve_candidate_generators_2020_01.csv), and the [two original specification files](../data/reference/curve_coverage/README.md). No manufacturer-specific curve was substituted into the resource or event models. Annual predominant-model labels and unresolved asset lineage still need verification before such substitution.

## Reproduce and verify

Created a separate clean Python **3.11.11** environment using `requirements-terrain.txt`, adding **numcodecs 0.16.6** for the recorded Blosc chunks. Existing scientific package pins and earlier environments are preserved. The [resolved snapshot](validated_terrain_linux_packages.txt) and `uv pip check` confirm compatible installed packages. The **current full suite** requires these extension dependencies:

```bash
python -m pip install -r requirements-terrain.txt
python -m unittest discover -s tests -v
```

The recorded public source manifest can be replayed into a cache; existing matching files are reused and changed bytes cause failure. Google object generations are used where recorded. If USGS or another source changes, retain the old snapshot and document a new source version rather than silently overwriting the study inputs.

```bash
python scripts/16a_fetch_terrain_references.py --manifest data/reference/terrain/source_manifest.json --output-dir /path/to/terrain_sources
python scripts/16_audit_wind_terrain.py --source-dir /path/to/terrain_sources --headless
```

Adding `--offline` to acquisition verifies existing files without network access. The validation replay checked **110 cached source files with zero downloads**. Curve-coverage reproduction uses `17_audit_curve_coverage.py --archive-source-dir /path/to/archive_sources`, containing the pinned GitHub tree response and the two included YAML specifications. That audit verifies the specification Git blob hashes and makes no network request.

All **72 tests** passed. Independent grid-index formulas and direct raw DEM-response checks reproduced all 103 site values, height conversions and summaries. Independent literal-label accounting reproduced all 49 curve groups and candidate capacities. Output/source hashes and [verification evidence](terrain_curve_verification.json) are retained; the figure was visually reviewed.

The next physical-validation need is independent wind information at representative sites and defensible turbine curves/asset identities. This stage adds terrain evidence and establishes the limited curve provenance available; it does not justify fitting a correction or starting the full climatology with validated-generation claims.
