# January 2020 event-definition comparison

This analysis compares the original irradiance proxy, modeled fixed-tilt PV output, and a 48-hour combined-energy definition. It uses the committed processed series; it does not estimate actual California fleet output, electricity shortages, or 2005–2024 event frequencies.

## Reference: each technology below 20%

The condition is wind CF <0.20 **and** solar value <0.20 at each hour. A reference prolonged event requires at least 24 consecutive such hours. Nighttime is included. For modeled PV, the solar value is AC capacity factor; for the legacy comparison it is the GHI/1000 proxy and is labeled accordingly.

| Solar series | Simultaneous low hours | Low-resource periods | Longest observed period | Periods ≥24 hours |
| --- | ---: | ---: | ---: | ---: |
| Original GHI proxy | 545 | 31 | 19 h | 0 |
| PV, tilt 25° | 504 | 31 | 19 h | 0 |
| **PV, tilt 35° baseline** | **502** | **31** | **19 h** | **0** |
| PV, tilt 45° | 501 | 31 | 19 h | 0 |

Each series covers the same 743 complete hourly intervals. Each has one low period touching the start boundary, whose full duration is unknown. Zero observed 24-hour events is a valid result; these thresholds have not been adjusted to manufacture events. The original pilot catalogues are preserved unchanged.

The hourly threshold follows the approach in [Li et al. (2021)](https://doi.org/10.3390/en14206508); the minimum 24-hour duration is our project criterion. See the earlier [definition review](event_definitions.md).

## Complement: 48-hour combined-energy windows

For wind share `a` of total rated wind-plus-PV capacity:

```text
combined_CF = a * wind_CF + (1 - a) * PV_AC_CF
```

The share is a **rated-capacity share**, not an annual generation share. Scenarios at 25%, 50%, and 75% wind are hypothetical portfolios. They do not describe California's actual fleet.

Calculate trailing means of **48 complete hourly intervals**, then flag windows with mean combined CF strictly below the threshold. Following the window-support approach described by [Mockert et al. (2023), Section 2.4](https://doi.org/10.1002/met.2141), include the hours contributing to qualifying windows. Our implementation explicitly merges overlapping or directly adjacent supports. Event duration is the number of unique covered hours, not the number of qualifying windows.

A low 48-hour mean does not require every individual hour to be low. A merged union period also does not imply every possible 48-hour mean within that period is below the threshold. Overlapping windows are not independent observations.

We evaluate thresholds 0.05, **0.06**, and 0.10 for each capacity mix and each of the three PV tilts: **27 cases**. The 0.06 value is a literature-comparison threshold from a German study, not an established California cutoff. Differences between this definition and the hourly definition involve aggregation, technology mixing, and thresholds; they are not a controlled test of smoothing alone.

### Baseline result

For 35° PV, 50% wind rated capacity, and threshold 0.06:

- 743 input hourly intervals produce **696 complete 48-hour windows**.
- The minimum 48-hour combined CF is **0.071207**, or **7.12%**.
- No complete window falls below 0.06, so no union event is detected.

### Mix and threshold sensitivity for 35° PV

| Wind rated-capacity share | Threshold | Qualifying windows | Union-covered hours | Observed merged events |
| --- | ---: | ---: | ---: | ---: |
| 25% | 0.06 | 0 | 0 | 0 |
| 50% | 0.06 | 0 | 0 | 0 |
| 75% | 0.06 | 135 | 199 | 1 |
| 25% | 0.10 | 28 | 75 | 1 |
| 50% | 0.10 | 208 | 303 | 2 |
| 75% | 0.10 | 581 | 743 | 1, with uncertain edge context |

At 75% wind and threshold 0.06, the one merged period spans **January 18 at 17:00 UTC to January 27 at 00:00 UTC**, covering **199 hours**. This is a result for a hypothetical wind-heavy portfolio and a union-of-windows definition, not 199 consecutive hours below 6% generation.

Event counts need not increase with threshold: previously separate periods can merge. Covered hours are therefore reported alongside event counts. The whole-record union at the most permissive listed case is boundary-limited, not evidence that a natural event lasted exactly 743 hours.

## Time alignment and boundary uncertainty

Wind snapshots are averaged once between adjacent times to approximate preceding-hour CF. Modeled PV already represents preceding-hour output and is **not smoothed again**. Legacy naive UTC labels and explicit UTC PV labels are normalized to UTC, then required to match exactly. Missing, duplicate, gapped, or out-of-range inputs are rejected.

Output timestamps label interval ends. The first interval starts at January 1 at 00:00 UTC; the last ends at January 31 at 23:00 UTC. The initial **47 rolling means are unavailable**, recorded as missing with `full_window_available=False`; they are not zero generation or complete nonqualifying windows.

Catalogues distinguish exact data-edge contact from `boundary_context_incomplete`. For the 48-hour method, unknown windows outside the record can overlap or adjoin events near either edge even when an event does not touch the exact boundary. We conservatively flag an event when it has fewer than 48 known hours before its start or after its end. Complete-event counts exclude these flags. The 199-hour example has enough context on both sides.

Long-term work should process contiguous periods with adequate preceding/following context and avoid counting an event separately in each monthly file.

## Reproduce from committed inputs

From the repository root, with the original pilot dependencies available:

```bash
python scripts/08_compare_event_definitions.py --headless
```

No raw ERA5 data, Copernicus credentials, or new download is required. The command reads the wind snapshot CSV, original proxy CSV, three modeled PV CSVs, and their model metadata. It checks that PV scenarios differ only in tilt and use the same source inputs. Metadata and checksums record the actual files used.

To run only the event tests:

```bash
python -m unittest discover -s tests -p 'test_energy_events.py' -v
```

The full suite, including PV tests, requires the optional PV dependencies:

```bash
python -m pip install -r requirements-pv.txt
python -m pip install -r requirements-terrain.txt
python -m unittest discover -s tests -v
```

## Outputs and verification

- [Baseline aligned series and rolling diagnostics](../data/processed/wind_pv_event_inputs_2020_01.csv).
- [Reference summary](../results/tables/pv_reference_summary_2020_01.csv), [periods](../results/tables/pv_reference_periods_2020_01.csv), and [duration sensitivity](../results/tables/pv_reference_duration_sensitivity_2020_01.csv).
- [All 27 rolling-window sensitivity cases](../results/tables/wind_pv_48h_sensitivity_2020_01.csv) and [merged period catalogue](../results/tables/wind_pv_48h_events_2020_01.csv).
- [Comparison figure](../results/figures/wind_pv_event_comparison_2020_01.png) and [run metadata](../results/tables/event_comparison_metadata_2020_01.json).
- [Machine-readable verification](event_comparison_verification.json).

All **22 tests passed**, including 12 event tests and the 10 existing PV tests. Independent direct-slice calculations reproduced the rolling means and explicitly marked window supports in all 27 cases; merged durations, window counts, and boundary flags agreed. The four hourly reference cases also matched direct calculations. The smallest rolling-mean distance from a tested threshold was about 5.62e-6, far above floating-point differences observed in the original wind reproduction.

These checks establish implementation consistency. The illustrative wind curve, uniform geographic deployment, administrative waters, inferred PV irradiance components, and system parameters remain model assumptions. January alone cannot establish rarity, seasonal patterns, comparisons with Germany, or temperature-extreme associations. Further model validation and multi-year data are needed for those scientific conclusions.

## Subsequent wind-model sensitivity

This comparison holds the original cubic wind curve and uniform wind-area weighting fixed. The later [wind assessment](wind_assessment.md) changes the curve and wind geography in a separate factorial experiment. Its results should not be substituted into this report without changing the scenario label. The original 199-hour result remains a conditional finding for its original wind/PV assumptions.

For the current complete suite, `requirements-terrain.txt` supplies all earlier runtime dependencies plus the optional terrain decoder; historical test counts above describe the saved stage.
