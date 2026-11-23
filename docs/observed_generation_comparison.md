# January observed-generation benchmark

On November 23, 2026, the project added a first comparison with official production records. It tests whether the modeled time variation resembles observed wind and solar output. It does **not** validate statewide capacity-factor amplitudes, identify a final best turbine curve, or validate Dunkelflaute event counts. The observation and model fleets are not matched.

## Sources and scope

- [CAISO production and curtailments archive](https://www.caiso.com/library/production-curtailments-data), [2020 workbook](https://www.caiso.com/documents/productionandcurtailmentsdata_2020.xlsx): use `Production` and `Curtailments`; inspect `Read_me`. The workbook describes reviewed raw data, supplied without operational/settlement-quality status. Production excludes reported curtailments. The archive remains available although publication of this report was discontinued in 2025.
- [EIA-923 annual-final data](https://www.eia.gov/electricity/data/eia923/), [2020 final-revision archive](https://www.eia.gov/electricity/data/eia923/archive/xls/f923_2020.zip): use the generation/fuel workbook, `Page 1 Generation and Fuel Data`, Excel header row 6. Extract rows with fuel WND or SUN and either state CA or reported balancing authority CISO. Retain source Excel row numbers and separate PV from solar-thermal prime mover ST.

Downloaded the two sources once and recorded archive/member checksums. Raw XLSX and ZIP files remain outside Git. The small derived tables and [source metadata](../results/tables/generation_observation_metadata_2020_01.json) are included. Annual EIA respondent frequency is retained; entries from annual respondents must not all be called directly reported monthly observations. Missing January values remain missing. Synthetic `State-Fuel Level Increment` rows, plant ID 99999, remain in state totals but are flagged and excluded from physical plant counts.

The following are **different reported populations**, not interchangeable observations:

| Source/population | January wind energy | January solar energy |
| --- | ---: | ---: |
| CAISO raw production archive | 991,545.496 MWh | 1,558,147.327 MWh, source Solar category |
| EIA California-state rows | 762,972.761 MWh | 1,468,672.459 MWh available PV entries; 65,564.000 MWh solar thermal |
| EIA rows with reported CISO BA | 748,408.868 MWh | 1,539,932.971 MWh available PV entries; 65,564.000 MWh solar thermal |

The totals have not been reconciled. State-versus-balancing-area boundaries alone do not explain the CAISO/EIA reported-CISO difference. Reporting population, aggregation, revisions and metering definitions require further investigation; do not treat their difference as model error or apply an undocumented adjustment. The EIA state PV selection has 42 rows with no numeric January entry, so its sum is explicitly an available-entry sum, not an assertion that unavailable entries generated zero. Three synthetic state PV increment rows contribute 752.899 MWh to the state sum.

All **101** plant IDs in the previous fixed wind inventory match EIA-923 wind rows, with 757,441.835 MWh of January generation. This establishes a path toward a plant-matched benchmark, but plant-ID matching does not establish generator-by-generator availability or the correct January capacity denominator. No observed CF is computed by dividing CAISO MW by the statewide 5,916.5 MW reference inventory.

## Time support and aggregation

Treat CAISO market hour 1 as 00:00–01:00 Pacific and interval 1 as its first five-minute interval. In the Production sheet, `Date` contains five-minute starts; check its clock against `Hour` and `Interval` for every retained row. Localize to `America/Los_Angeles` and convert to UTC. **The workbook's Read_me does not explicitly name a timezone**; Pacific market time and start labeling are documented interpretation assumptions, supported by the clock fields and daytime solar pattern, rather than claimed to be an explicit statement in that sheet. This importer deliberately supports January 2020 only; it does not silently resolve DST transitions.

There are **8,928 consecutive five-minute records**, yielding **744 complete hourly observations**. Average exactly twelve MW values per hour and label the result by UTC interval end. Verify energy conservation: the sum of five-minute MW divided by 12 equals the sum of hourly MW × 1 hour. Missing/duplicate/partial production intervals fail; they are not filled with zero.

Curtailments are a sparse table. Unlisted intervals and blank fuel cells represent no listed curtailment for that fuel, per the table's description. Keep them in separate columns and never add them to the production series for this comparison. Summed January curtailments round to **7,933 MWh wind** and **130,070 MWh solar**, consistent with the published [January renewables performance report](https://www.caiso.com/documents/monthlyrenewablesperformancereport-jan2020.html). That report's maximum-production figures differ from this raw archive's maxima; no equality or settlement-quality reconciliation is asserted.

The existing model covers 743 intervals in UTC January. A Pacific January extends into UTC February. Its common support with these observations is therefore **735 intervals**, ending January 1 at 09:00 UTC through January 31 at 23:00 UTC. Eight model intervals precede the local observation month; nine observed hours at the month's end lack model output. No endpoint is shifted to manufacture full-month coverage.

For daily diagnostics, assign each interval to its **start's local date**. In particular, an interval ending at local midnight belongs to the preceding day. Use only 24-hour complete days: **January 1–30**, 30 days. Drop the partial January 31 from daily statistics.

## Shape calculations and results

Use all eight already defined wind scenarios and the original 35° fixed-tilt PV baseline; no parameters or lags are fitted. Compute Pearson correlation, correlation of adjacent hourly differences, and RMSE after dividing each series by its **own mean on the same support**. The latter is a dimensionless shape error, not CF RMSE. Daily scaling uses the means over complete daily pairs.

| Wind scenario | Hourly correlation | Daily-mean correlation |
| --- | ---: | ---: |
| Cubic, uniform | 0.341 | 0.503 |
| Cubic, capacity locations | 0.783 | 0.883 |
| WTK IEC I, uniform | 0.358 | 0.515 |
| WTK IEC I, capacity locations | 0.793 | 0.887 |
| WTK IEC II, uniform | 0.363 | 0.518 |
| WTK IEC II, capacity locations | 0.796 | 0.888 |
| WTK IEC III, uniform | 0.378 | 0.528 |
| WTK IEC III, capacity locations | 0.808 | 0.895 |

Holding the cubic curve fixed, changing geography raises hourly correlation from 0.341 to 0.783. This is evidence that representative deployment matters for the modeled temporal shape. It is not an out-of-sample accuracy ranking of the curves or evidence that modeled CF levels are correct. For the IEC II location scenario, hourly first-difference correlation is only **0.245**, despite level correlation of 0.796; short-term ramps remain substantially less well reproduced.

PV hourly correlation is **0.969**, correlation during the **316** hours with positive modeled PV is **0.912**, and correlation between complete daily means is **0.641**. The day–night cycle strongly contributes to the hourly value. Daily results are still based on only 30 days and may include seasonality; they do not isolate weather skill. The observed Solar category is not assumed to consist solely of fixed-tilt PV, and trackers, siting, temperature effects, losses and curtailment remain relevant differences.

See [all metrics](../results/tables/observed_shape_metrics_2020_01.csv), [paired hourly data](../data/processed/observed_shape_comparison_2020_01.csv), [daily means](../results/tables/observed_shape_daily_means_2020_01.csv), and [comparison figure](../results/figures/observed_generation_shapes_2020_01.png). Hourly/daily observations are autocorrelated, and this single month is not an independent validation sample. No significance claims or observed-event classifications are made.

## Reproduce and verify

The comparison uses committed CSVs and makes no network request:

```bash
python -m pip install -r requirements-wind.txt
python scripts/11_compare_observed_shapes.py --headless
python -m unittest discover -s tests -v
```

To rebuild the observations from separately downloaded originals, supply their paths and actual retrieval date:

```bash
python scripts/10_prepare_generation_observations.py --caiso-workbook /path/to/productionandcurtailmentsdata_2020.xlsx --eia923-archive /path/to/f923_2020.zip --retrieved-on YYYY-MM-DD
```

Used the existing clean Python 3.11.11 Linux environment and pinned wind requirements; no additional packages were installed. All **42 tests** passed, including nine observation tests. Independent direct Excel-row and array calculations checked the source selections, all hourly production/curtailment aggregates, energy conservation, time intersection, complete local days, all nine scenario metric rows and artifact hashes. See [verification](observed_generation_verification.json). Tests exposed and resolved a pandas timestamp-resolution assumption: duration checks compare actual timedeltas rather than assuming `.asi8` integers always represent nanoseconds.

## Next requirements for amplitude validation

Reconcile the EIA and CAISO source populations, reconstruct a January-specific operating inventory, select compatible observed and modeled plant groups, and obtain the missing ERA5 boundary hours. Match solar PV technology and AC capacity denominators separately from solar thermal and distributed systems. Then compare energy/CF magnitudes on identical support, quantify losses and uncertainty, and test another period without tuning to January. Earlier event results remain unchanged; a full 2005–2024 analysis has not yet been run.

## Follow-up: plant-matched energy assessment

The [January inventory/energy diagnostic](january_wind_match.md) now matches whole plants and bounds missing model hours. It finds an energy shortfall despite the shape agreement reported here; this report's correlations must not be interpreted as amplitude validation. The follow-up also clarifies EIA frequency: Schedule 3D requires wind/solar annual respondents to provide monthly operations. An A flag alone implies neither annual-only observations nor allocated monthly estimates. The additional EIA-930 audit preserves rather than clips signed net-solar values and leaves the operational-versus-plant population difference unresolved.
