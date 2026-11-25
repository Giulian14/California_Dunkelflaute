# Study protocol before archive expansion

Recorded November 24, 2026. This separates the confirmed research design from model choices that still need evidence. It does not describe an executed 2005–2024 analysis.

November 25 follow-up: the [full-paper and pinned-code review](paper_method_comparison.md) confirms Li's fixed-2016-fleet precedent and documents the California adaptations below. No prior scientific outputs were changed. A [limited validation request plan](limited_validation_download.md) is prepared but unsubmitted.

## Confirmed study meaning: a fixed reference system

The author selected **a fixed reference wind/solar layout**, with year-specific fleets for validation, on November 24. The question is how different years of weather affect the **same renewable system**. Keeping locations, rated capacities and technology assumptions constant prevents deployment growth, relocation and equipment changes from being mistaken for weather trends. The result is a counterfactual weather-driven resource assessment, not reconstructed historical generation or historical grid reliability.

Li et al. (2021), §2.1, p. 4, explicitly apply 1985–2016 weather to a fixed 2016 fleet. This is published support for the design principle. Their energy forcing is MERRA-2 via Renewables.ninja; our ERA5/2020-EIA implementation remains a California adaptation, not a replication of their energy dataset.

Weather trends can still reflect reanalysis uncertainty and observational-system changes. A fixed layout removes the fleet-change confounder; it does not remove every source of uncertainty. Comparisons with observed generation must use each observation period's matched assets and capacities, rather than treating the reference fleet as that year's actual fleet.

**Working reference:** 2020 EIA-860 utility-scale onshore wind and photovoltaic sites within the saved California boundary. The existing wind reference is already an explicitly hypothetical fixed year-end 2020 layout. Its inclusion rules must be reconciled with the final PV inventory and frozen in a hashed generator/weight manifest before production. Solar thermal, offshore wind, behind-the-meter PV, imports and storage are outside this proposed resource-system scope. The administrative-state temperature mask includes state waters; document that support rather than calling it land-only California.

**Not yet selected:** final wind curves/corrections, tracker treatment, fleet PV losses and the complete fixed PV weights. The area-weighted pilot is retained as a sensitivity, not silently relabeled as deployment-weighted. Reference-year choice and spatial weights must be explicit sensitivities. Current matched-cohort wind and fixed-tilt PV amplitude discrepancies prevent claiming a validated final physical model.

## Calendar and boundary rules

- Core exposure is `[2005-01-01 00:00, 2025-01-01 00:00)` UTC: **175,320 hours**. End labels are one hour later than the corresponding interval starts.
- Acquire December 2004 and January 2025 as context. This is sufficient for ordinary 48-hour windows, but does not guarantee very long events end inside the downloaded range. Keep censoring flags.
- Carry one preceding instantaneous sample across weather files. Radiation is the preceding-hour ERA5 energy accumulation divided by 3,600; temperature/wind snapshot handling follows the documented model. Reject gaps and incompatible products. Do not fill missing observations with zero.
- Detect events globally on joined hourly resources with context. Retain catalogues of events intersecting the core. Report core-clipped exposure/deficits separately from whole-event observed duration. Flag clipped or context-incomplete events; do not treat their durations as fully observed.
- Assign onset counts to the UTC year containing the observed onset **only when that onset is established**. Report left-censored overlaps separately. Count an episode crossing New Year once; split its exposure hours by year without creating a second episode.
- Pacific-month observed generation comparisons retain their own support convention. Do not silently shift the climate-study calendar to match those comparisons.

## Predefined event analyses

Retain both existing families, separately named. Do not pick the family, threshold or physical model because it produces a preferred number of January events.

The November 25 review recommends the simultaneous-hourly family as the primary reference and combined 48-hour family as complementary. The pilot's `>=24h` duration criterion remains preserved; add a separately labeled `>24h` (minimum 25 hourly intervals) compatibility comparison when following Li's prolonged-event figures exactly. Mockert's German 0.06 threshold was selected partly to resemble earlier German event counts; it is not an event-frequency target for California. The current author code differs at boundaries/extraction from our full-window support unions; see the review before claiming exact reproduction.

| Analysis | Definition | Interpretation |
| --- | --- | --- |
| Simultaneous hourly lows | Both wind and PV AC CF strictly below 0.20 for at least 24 consecutive hours | An absolute resource criterion including night; not a climatological rarity percentile |
| Combined low energy | Complete trailing 48-hour mean of `0.5 × wind CF + 0.5 × PV CF` strictly below 0.06 | Union of all qualifying windows' hourly support; covered hours need not each be below 0.06 |
| Registered sensitivities | Wind rated-capacity shares 0.25/0.50/0.75; combined thresholds 0.05/0.06/0.10; durations 6/12/18/24/48 hours for hourly runs; documented physical-model alternatives | Compare the full predefined grid, including zero-event cases |

The 50/50 mix is a **rated AC capacity share**, not a measured California energy share. These literature-inspired thresholds are trial reference definitions, not established California adequacy limits. A low monthly mean caused by a biased wind model can distort absolute-threshold counts; passing software tests does not resolve that problem. See [event definitions](event_definitions.md) for the literature and support conventions.

Report annual onset counts, exposure hours, observed duration distributions and censoring. For energy-style severity, report the positive deficit integral `Σ max(0, threshold − combined CF) × 1 hour` within event support and the core. Its unit is MWh per MW of reference rated capacity. It is a shortfall relative to a trial resource threshold, **not unserved demand**. Do not call all window-union hours continuously low. Seasonal rarity, if added later, must use a separately documented baseline and label rather than replacing the absolute threshold post hoc.

## Temperature and coincidence

The implemented working method uses the **UTC daily mean of the statewide administrative-area temperature series**, with cosine-latitude spatial weights. Average the 24 complete end-labeled hourly interval means belonging to the day. Midnight interval ends belong to the preceding day. Incomplete edge days are flagged and excluded; interior gaps fail. This temperature describes statewide background conditions. It is not local maximum temperature, population exposure, demand or a regional heatwave index.

The 5/95% thresholds and three-day run below are a project-specific extension, **not prescribed by either uploaded paper**. Mockert uses temperature anomaly composites relative to a 30-day running-mean climatology and a separate modeled demand series; Li does not supply our heat/cold index. Keep percentile extremes, climatological anomalies and demand distinct.

Use the 2005–2024 **study-sample baseline**, not a purported standard 30-year climatological normal. For each target year, exclude that entire year when estimating the seasonally varying 5th/95th percentiles. Pool the other years' daily means in a circular ±15-calendar-day window on a 365-day reference calendar. Require at least 18 complete other years; use NumPy's linear quantile estimator. Exclude February 29 from the fitting pool and interpolate its thresholds from February 28/March 1. Days strictly above/below the respective percentiles are hot/cold; a sustained episode needs at least three consecutive days. Keep boundary-censored runs distinct. These settings are fixed before inspecting long-term extreme counts.

[Temperature helpers](../scripts/temperature_extremes.py) and [calendar/baseline tests](../tests/test_temperature_extremes.py) implement those definitions. **No real temperature-extreme climatology has been estimated yet.** A January pilot cannot supply the required independent baseline years.

Planned coincidence summaries will report renewable-event exposure hours overlapping hot/cold-day support and the fraction of established renewable episodes intersecting sustained temperature episodes. Keep episode and hour denominators separate. Compare coincidence with the seasonal baseline occurrence rate; raw overlap alone does not establish dependence. Report interannual uncertainty using year-block resampling of annual summaries, with cross-year episodes assigned consistently. Regional/local-day temperature indices and alternative baselines remain explicit sensitivities, not interchangeable versions of this statewide UTC index. The overlap/uncertainty estimators remain to be implemented and checked on the final dataset; no inference is claimed here.

## Validation and release gates

1. Resolve or explicitly quantify wind underprediction and fixed-tilt PV overprediction using defensible physical/site evidence. Do not fit arbitrary multiplicative factors to January alone.
2. Validate the selected parameters against matched populations in a contrasting season and another year, with parameters fixed in advance. The five-cell public-weather rehearsal checks processing only.
3. Run a limited **direct-CDS, full-grid** adjoining-month rehearsal with the selected reference inventories. Verify source convention/version, restart receipts, resource output fingerprints, wall time/storage and observed-model support. The existing secondary-source exercise cannot establish interchangeability with CDS forcing.
4. Freeze inventory/curve/configuration hashes and export all QC failures before submitting the full request plan. Do not silently turn unresolved data into missing/zero generation.

The author's fixed-layout choice is settled. The remaining gates require evidence and implementation, not another approval of that choice. The [readiness record](expansion_readiness.md) records their current status.
