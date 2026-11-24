# Readiness for the 2005–2024 study

Status as of November 24, 2026. This is a scientific and processing worklist, not an approval requirement. Keep it consistent with the [research log](research_log.md). Only January 2020 weather has been numerically modeled so far; a 20-year climatology has not been calculated.

## Priority before adopting the long-term model

| Check | Current evidence | Remaining work |
| --- | --- | --- |
| Wind amplitude and physical assumptions | **Open.** The stricter 103-plant comparison gives observed nominal CF 16.92% versus nearest IEC II bounds 9.85%–11.06%. Bilinear sampling lowers output further. | The latest terrain/curve audit supplies 103 DEM references and identifies limited candidate provenance; inspect high-residual sites and obtain defensible turbine curves/hubs and an independent wind reference. Separate model correction from uncertainty; test changes on an unused period. |
| Asset identities and capacity denominators | **Partly checked.** Monthly snapshots, whole-plant rules, annual unit capacities and exclusions are recorded. Two capacity increases suggest unresolved reporting consolidation. | Establish defensible asset lineage and a compatible generation population. Treat the 103-plant subset as conservative evidence, not a fully reconstructed operating fleet. |
| Coordinate and wind mechanics | **Checked for the pilot.** Monthly/annual coordinates agree within four metres; field units, vector flags, chronology and nearest/bilinear calculations pass checks. | Public ERA5 terrain and 103 USGS DEM points are now compared; median absolute point/grid height difference is 205 m. Verify turbine/farm footprints and independent wind: terrain differences alone do not establish the bias cause. |
| PV amplitude | **Open.** Timing/daylight and tilt sensitivity were checked; BA-wide shape correlation is not plant-matched PV energy validation. | Match PV-only generation to AC capacity and siting; assess tracker/fixed-tilt mix, losses, temperature and radiation decomposition. Keep solar thermal and distributed PV populations explicit. |
| Other seasons/years | **Open.** January alone cannot validate seasonal behavior or support out-of-sample model selection. | Add at least a contrasting season and another year using preselected parameters. Report wind/PV energy and temporal errors on matched populations; do not select thresholds to produce events. |

The existing evidence does not justify choosing a model simply because its output is higher. Nor would adding wake/availability losses by itself explain modeled energy already below observed net production. Keep possible terrain, turbine and reporting explanations separate until data establish their contributions.

## Processing checks before the full production run

1. **Fix study meaning and geography.** Decide whether the primary result describes a fixed reference renewable deployment exposed to 20 years of weather, or the changing historical fleet. A changing fleet can confound weather trends with deployment changes. Document wind/solar rated-capacity shares and regional/statewide footprints. Use year-specific matched fleets for validation where needed without silently changing the climate-study reference.
2. **Define the study calendar and input support.** A proposed UTC core interval is `[2005-01-01 00:00, 2025-01-01 00:00)`, totaling **175,320 hours**, including five leap days. Its hourly interval-end labels run from January 1, 2005 at 01:00 to January 1, 2025 at 00:00 UTC. Obtain bracketing instantaneous samples and accumulated radiation at the required end labels, including the final boundary timestamp. Include explicit window/event context outside the core and retain any remaining censoring flags. Pacific-month validation is a separate support convention, not a silent shift of the climate record.
3. **Prove chunk continuity.** The [November 24 verification](chunk_continuity.md) now passes real January partitions (two/six files), all 18 tested window cases and synthetic New Year/leap/nonleap boundaries. The chosen architecture carries one weather bracket and joins compact hourly means before global rolling/event calculations, preserving context without per-file resets. Real contiguous multi-month data, source-version changes and resumable production still need a rehearsal. January-only observation importers remain restricted; aware DST resource-label conversion was tested, but ambiguous naive local labels are rejected.
4. **Audit every input batch.** Check expected variables/units, product-specific accumulation meaning, grid/coordinate agreement, duplicates/gaps, missing values and ERA5 version metadata. Preserve download requests, checksums and retrieval/source versions. Treat unavailable data as missing, rather than low generation. Reuse existing raw files and keep them outside Git.
5. **Predefine event analysis.** Specify absolute versus seasonally normalized thresholds, capacity mix, minimum duration and hourly-versus-window support. Preserve the union-of-qualifying-windows interpretation and incomplete-boundary context. Assess sensitivity to reasonable thresholds and model uncertainty; January's zero baseline event count is a conditional scenario result, not validation of a definition.
6. **Define temperature comparisons.** Choose heat/cold reference climatology, seasonal percentiles or anomalies, spatial support and local-day timing before interpreting coincidences. Energy-weighted sites and a statewide administrative temperature average answer different questions.
7. **Run a multi-month rehearsal.** Confirm reproducibility, output metadata, memory/storage needs and resumable acquisition on a small continuous range. Then process the larger archive using the tested pipeline and review QC summaries before making frequency/severity claims. Sparse extreme events and autocorrelation require explicit uncertainty treatment in the final study.

No additional access or user-side environment change was needed for the latest diagnostics. Further physical and held-out validation will need additional weather/site reference inputs; scope those downloads to the specific checks first. Copernicus credentials, if needed for retrieval, belong in the configured client environment rather than in chat or Git.

## Evidence completed

- [Original workflow reproduction](full_workflow_verification.md).
- [PV implementation and sensitivity](pv_model.md), [event comparison](event_comparison.md), and [wind curve/location sensitivity](wind_assessment.md).
- [Observed temporal shapes](observed_generation_comparison.md), with unmatched-population limits.
- [Initial January inventory and missing-hour bounds](january_wind_match.md), now qualified by the annual-capacity audit.
- [Site/capacity diagnostics](wind_site_diagnostics.md) and [verification](wind_site_verification.json).
- [Terrain/curve-provenance audit](wind_terrain_and_curve_audit.md) and [verification](terrain_curve_verification.json).
- [Latest file/calendar continuity check](chunk_continuity.md) and [verification](continuity_verification.json).

The current suite has **85 passing tests**. Tests establish the checked calculations and data handling; they do not close the open physical-validation questions above.
