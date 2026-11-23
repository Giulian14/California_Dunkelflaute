# Wind curve and geographic weighting assessment

The November 23, 2026 assessment separates two wind-model assumptions: the power curve and geographic capacity distribution. It uses the existing January ERA5 inputs and retains every earlier pilot and PV result. This is a controlled sensitivity analysis, not validation against observed generation.

## Factorial design

Compare four curves with two fixed geographic weightings, giving eight wind scenarios. Hold the 100 m wind field, hourly alignment, 35° PV model, and event definitions fixed. PV continues to use its original uniform-area weighting; only wind geography changes.

The curves are the original illustrative cubic and three published normalized WTK onshore reference curves:

| Curve | Cut-in | Rated speed from source specification | Cut-out | Reference hub height |
| --- | ---: | ---: | ---: | ---: |
| Original cubic | 3 m/s | 12 m/s | 25 m/s | 100 m scenario |
| WTK IEC I | 3 m/s | 17 m/s | 25 m/s | 100 m |
| WTK IEC II | 3 m/s | 14 m/s | 25 m/s | 100 m |
| WTK IEC III | 3 m/s | 12 m/s | 22 m/s | 100 m |

The [official turbine-models archive](https://github.com/NatLabRockies/turbine-models) identifies these as theoretical reference models. Its [IEC II documentation](https://natlabrockies.github.io/turbine-models/WTK_Validation_IEC-2_normalized.html) traces them to King, Clifton and Hodge (2014), *Validation of Power Output for the WIND Toolkit*, NREL/TP-5D00-61714, which uses normalized curves with 2 MW ratings and 100 m hubs. This avoids introducing an arbitrary vertical extrapolation solely to compare curves.

The original CSVs, YAML specifications, BSD notice, immutable source commit and checksums are included in [data/reference/wind_curves](../data/reference/wind_curves/manifest.json). Linear interpolation is used between tabulated speeds. Output is zero below cut-in and **strictly above** documented cut-out; the source's endpoint power is retained. In particular, the IEC III curve is not linearly ramped from full output at 22 m/s to zero at 23 m/s. The preserved cubic retains its original shutdown **at or above** 25 m/s. These endpoint conventions are explicit rather than silently modifying the published data.

No individual curve is claimed to match all California turbines. IEC II is a central comparison case, not a fit to desired event counts.

## Fixed EIA capacity-location reference

The source is the official [EIA-860 annual inventory](https://www.eia.gov/electricity/data/eia860/), specifically the [2020 archive](https://www.eia.gov/electricity/data/eia860/archive/xls/eia8602020.zip). EIA collects generator-specific capacity and operating information for surveyed plants with at least 1 MW combined nameplate capacity and provides plant coordinates. This is not a census of all small distributed wind installations.

Read the `Operable` sheet of `3_2_Wind_Y2020.xlsx` and join `2___Plant_Y2020.xlsx`, sheet `Plant`, by plant code. Headers are on the second worksheet row. Retain `State=CA`, technology `Onshore Wind Turbine`, status `OP`, positive nameplate MW, valid ERA5-domain coordinates, and location inside/on the saved California boundary. Duplicate plant/generator identities or duplicate plant-coordinate joins fail rather than double-count capacity.

| Selection quantity | Result |
| --- | ---: |
| CA onshore generator candidates | 122 |
| Candidate nameplate capacity | 5,970.6 MW |
| Retained OP generator records | 117 |
| Retained plants | 101 |
| Retained capacity | 5,916.5 MW |
| Excluded out-of-service records | 5 |
| Excluded capacity | 54.1 MW |
| Occupied nearest ERA5 centers | 25 |

All retained points passed geographic screening; none maps to an outside-mask center in this dataset. The five exclusions and their status codes are preserved in a separate table. Source ZIP and workbook hashes, boundary hash, selection rules and derived-file hashes are in [inventory metadata](../data/reference/eia2020_ca_wind_metadata.json).

The EIA instructions in the archive specify existing equipment as of December 31 of the reporting year. Thus this is a **fixed end-of-2020 layout**, not actual January 2020 operating capacity or hourly availability. The capacity-weighted reported hub height is **73.26 m**. Keeping wind at 100 m is a controlled reference assumption, not a claim that those units operated at 100 m.

## Spatial and temporal calculations

1. Compute speed as `hypot(u100, v100)` at every ERA5 center and timestamp. Reject missing values and unexpected wind units.
2. Apply each nonlinear power curve at each center before aggregation.
3. For uniform deployment, normalize `cos(latitude)` over the same 695 administrative centers used in the pilot.
4. For capacity-location deployment, assign each EIA plant to the nearest center along each coordinate axis. Ties use the first coordinate in file order. Add each plant's wind-generator nameplate MW to its center, then divide by total MW. **Do not multiply these capacity shares by latitude weights again.**
5. A plant point may be inside California while its nearest center lies outside the administrative grid-center mask. Preserve such a mapping and report it rather than moving or dropping its capacity; the actual dataset has zero such cases.
6. Aggregate the snapshot CFs, then average adjacent snapshots once to approximate preceding-hour generation. The fixed linear spatial weights commute with this endpoint average; nonlinear power conversion does not commute with averaging speed.

The resulting outputs have 744 wind snapshots and **743 complete hourly intervals**. The original cubic/uniform series agrees with the preserved pilot within float32 relative precision. Reported scenario means below use the 743 intervals, not the slightly different 744-snapshot means.

## January results

| Curve | Uniform mean CF | Capacity-location mean CF |
| --- | ---: | ---: |
| Cubic | 0.047307 | 0.057431 |
| WTK IEC I | 0.058478 | 0.074495 |
| WTK IEC II | 0.074876 | 0.099237 |
| WTK IEC III | 0.090360 | 0.125612 |

For IEC II, changing the curve while retaining uniform weights raises mean modeled CF from 4.73% to 7.49%; changing only geography under the cubic gives 5.74%; changing both gives 9.92%. These are model sensitivities, not an accuracy ranking. The factors have an interaction: changing the curve has a different effect at capacity locations than across the uniformly weighted state.

All eight scenarios produce **zero observed ≥24-hour simultaneous events** and **zero baseline 48-hour union events at 50/50 wind/PV rated capacity and threshold 0.06**. That January outcome is robust within these tested cases, not a result for the entire 2005–2024 period.

Across the 72 combinations of wind scenario, capacity mix and threshold, wind-heavy outcomes change. For example, at 75% wind and 0.06, the original cubic/uniform scenario has one 199-hour union period; IEC II with capacity locations has two observed periods, one with incomplete boundary context. The detailed catalogue retains those flags. Overlapping low-mean windows are merged by support; union duration is not the number of window endpoints and does not mean every hour has low generation.

## Reproduce

The small extracted inventory and reference curves are included. With existing ERA5 wind and mask files plus the committed PV baseline, run:

```bash
python scripts/09_assess_wind_model.py --headless
```

To reproduce workbook extraction, download the official archive separately, then run:

```bash
python -m pip install -r requirements-wind.txt
python scripts/00_prepare_eia_wind_inventory.py --archive /path/to/eia8602020.zip --retrieved-on YYYY-MM-DD
python -m unittest discover -s tests -v
```

Supply the actual archive retrieval date, or omit that flag if unknown. Preparation makes no automatic network request. The raw archive and workbooks are not committed. `requirements-wind.txt` adds openpyxl 3.1.5 to the existing PV dependencies; [resolved Linux versions](validated_wind_linux_packages.txt) are recorded separately.

Outputs include snapshot/hourly series, plant-to-grid assignments, normalized grid weights, scenario summaries, reference periods, 72 event sensitivity rows, merged-window catalogues, a four-panel figure, and input-checksum metadata.

## Verification and limits

All **33 tests** passed: 11 new wind/inventory tests plus the existing 22 PV/event tests. Independent filtering reproduced the EIA row count, plant count and MW total. Independent nearest-center/MW accumulation matched the weights; independent searchsorted/linear-blend calculations matched all six published-curve/weight time series to numerical precision. Independent hourly and direct-slice window calculations matched all eight reference cases and all **72** event sensitivities. See [machine-readable checks and output hashes](wind_assessment_verification.json).

The calculation uses nominal curve behavior without additional density, wake, curtailment or availability corrections. Wind therefore represents reference turbine potential, whereas PV includes the stated system/inverter losses; loss-model consistency remains part of final physical-model validation. Nearest-grid plant centroids do not resolve wind-farm extent, turbine micrositing or mountain-pass flow. The 101 plant points occupy 25 weather cells and are not independent weather samples. Actual hubs differ from the controlled 100 m height, and PV siting is unchanged. Observed-generation validation, a justified final reference deployment, and continuous multi-year processing remain necessary before making historical climatological or system-adequacy claims.

The dated [research log](research_log.md) records this stage and the earlier steps needed for later methods writing.

## Subsequent production comparison

The [first observed-generation benchmark](observed_generation_comparison.md) compares the temporal shapes of all eight preserved scenarios with CAISO production. Capacity-location weights improve January shape agreement, but populations and capacity denominators remain unmatched. The benchmark does not supersede this assessment's amplitude limitations or establish a final best curve.
