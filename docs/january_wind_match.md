# January wind inventory match and bounded energy diagnostic

The November 23, 2026 follow-up matches EIA plant-level January generation to a conservative monthly wind inventory. It finds a substantial energy shortfall in all four reference-curve scenarios. This changes the interpretation of the earlier strong timing correlation: geographic weighting improves shape agreement, but the model's energy level still needs investigation before a multi-year study.

## Inventory and plant matching

Use the official [EIA-860M archive](https://www.eia.gov/electricity/data/eia860m/), specifically [December 2019](https://www.eia.gov/electricity/data/eia860m/archive/xls/december_generator2019.xlsx) and [January 2020](https://www.eia.gov/electricity/data/eia860m/archive/xls/january_generator2020.xlsx). Both are preliminary month-end inventories. Verify each workbook's title and read the `Operating` sheet with header on Excel row 2. Retain CA-state Onshore Wind Turbine records with all status categories visible; do not equate the sheet name with OP status.

| Inventory stage | Generator records | Plants | Nameplate MW |
| --- | ---: | ---: | ---: |
| December operating-sheet wind, all statuses | 137 | 117 | 6,166.2 |
| December OP | 135 | 116 | 6,148.7 |
| January operating-sheet wind, all statuses | 131 | 112 | 6,099.5 |
| January OP | 129 | 111 | 6,082.0 |
| Final matched cohort | 123 | 106 | 5,985.7 |

The monthly January inventory differs from the previously used fixed end-2020 reference, whose OP screening retained 5,916.5 MW. Preserve that older scenario; the new cohort serves this January diagnostic and does not define a historical 2005–2024 fleet.

Require each whole plant's wind generator identities, statuses, capacities, operating dates, fuel and prime mover to agree across both snapshots. Every wind unit must be OP, in service before January, have positive capacity, and have consistent valid in-boundary coordinates. Then match one CA/WND/WT EIA-923 January row per plant. Exclude a whole plant if any wind unit fails or changes; matching plant MWh to only its surviving generators could give a false CF. Reject duplicate generator or generation keys. Missing generation stays missing; an observed CF outside 0–1 is flagged, and the model comparison stops for investigation rather than silently screening that value away.

Six generator keys disappear between snapshots. The January `Retired` sheet records five retirements in **January 2020 totaling 64.9 MW**, plus one **December 2019 retirement of 1.8 MW** that was still in the December operating snapshot. The latter illustrates reporting lag; snapshot differences cannot all be labeled January retirements. The affected GE–Tehachapi plant retains two units, but its entire 5.3 MW remaining plant is excluded under the whole-plant rule.

Three otherwise stable plants have no matching WND/WT EIA-923 row: Mojave 18 (50823), Mojave 3 (52143), and Mojave 5 (52144), totaling **86.5 MW**. No names or inferred successor IDs are substituted. Two other plants contain non-OP wind records: Dinosaur Point and CTV Power Purchase Contract Trust. The latter also contains a 4.5 MW OP unit; it is excluded with the rest of its plant to avoid a partial denominator.

The retained **106 plants / 123 generators / 5,985.7 MW** have **759,921.181 MWh** of January net generation, covering **99.6000%** of the 762,972.761 MWh in the EIA CA-state wind selection. Excluded rows account for 3,051.580 MWh; included plus excluded energy reproduces the state total. All retained plant nominal monthly CFs lie in 0–1. See [all plant decisions](../data/reference/jan2020_wind_plant_audit.csv), [generator transitions](../data/reference/jan2020_wind_generator_transition.csv), [retirements](../data/reference/jan2020_wind_retirements.csv), and [source/checksum metadata](../data/reference/jan2020_wind_inventory_metadata.json).

The resulting observed nominal monthly CF is `759921.181 / (5985.7 × 744) = 0.17063993`. Monthly snapshot agreement supports this fixed **installed-nameplate reference denominator**; it does not prove hourly availability or exclude unreported within-month changes. Availability hours are not subtracted from the installed-capacity denominator. Assume EIA January calendar-month energy for California plants corresponds to Pacific January; the monthly file does not expose hourly metering boundaries.

EIA respondent frequency is a submission schedule. [Form EIA-923 Schedule 3D](https://www.reginfo.gov/public/do/DownloadDocument?objectID=126697301) requires wind/solar annual respondents to provide operations for **each month**. An A flag alone does not establish annual-only data or an estimated monthly allocation. Preserve the flag and missing values, but do not discard annual respondents on that basis.

## Model calculation and missing-hour bounds

Keep the original four reference curves and 100 m ERA5 wind, with no parameter fitting, gain correction or threshold changes. Assign each matched whole plant to its nearest ERA5 center and weight by nominal MW; apply each curve before averaging adjacent snapshots once. No additional latitude factor or land-mask relocation is applied. The cohort occupies 24 ERA5 centers; none of its nearest centers lies outside the administrative mask. Report the mapping and input hashes in [run metadata](../results/tables/matched_january_wind_metadata_2020_01.json).

The existing weather files provide **735** hourly intervals within Pacific January. Nine end-of-month hours are unavailable. Do not substitute zeros or extrapolate the weather. For any selected reference curve, its missing hourly CF must lie in 0–1. If `S` is the sum of known hourly CFs, then:

```text
full-month CF lower bound = S / 744
full-month CF upper bound = (S + 9) / 744
energy bounds in MWh = CF bounds × 5985.7 MW × 744 h
```

This is a deterministic bound on missing support **within the chosen model**, not a confidence interval or a bound on all physical-model error. Its width is 9/744, or 1.2097 CF percentage points. No particular value inside the interval is presented as an estimated full-month CF.

| Curve | Monthly model CF bounds | Observed nominal CF | Minimum shortfall relative to observed energy |
| --- | ---: | ---: | ---: |
| Original cubic | 5.69%–6.90% | 17.06% | 59.59% |
| WTK IEC I | 7.38%–8.59% | 17.06% | 49.67% |
| WTK IEC II | 9.83%–11.04% | 17.06% | 35.31% |
| WTK IEC III | 12.44%–13.65% | 17.06% | 19.99% |

For IEC II, the model energy upper bound is **491,592.763 MWh**, compared with **759,921.181 MWh** observed for the matched plants. Even assigning full output to every missing hour leaves at least **268,328.418 MWh**, or **35.31%**, of observed energy unexplained. All four model upper bounds are below observed net energy. This finding is conditional on the cohort, nominal capacities, calendar support and stated model; it does not uniquely diagnose a cause.

ERA5 grid-scale wind in complex terrain, plant centroids versus turbine positions, generic curves and actual turbine/hub specifications require investigation. The model is at 100 m and has no explicit density, wake, availability or curtailment corrections; EIA energy is net production. Extra physical loss factors would reduce modeled energy, so adding losses alone cannot resolve this shortfall. There is no justification for a fitted multiplier or a climatological event-frequency claim from this one-month result.

See the [summary bounds](../results/tables/matched_january_wind_bounds_2020_01.csv), [424 plant/curve bounds](../results/tables/matched_january_wind_plant_bounds_2020_01.csv), [known hourly model series](../data/processed/matched_january_wind_known_hours_2020_01.csv), and [figure](../results/figures/matched_january_wind_bounds_2020_01.png). Earlier files and event counts remain unchanged scenario outputs; they are not validated climatological estimates.

## Additional generation-source audit

Retrieved EIA-930 CISO hourly wind and solar using the official [API v2 fuel-type route](https://api.eia.gov/v2/electricity/rto/fuel-type-data/). Its route metadata identifies `hourly` as UTC; [EIA's documentation](https://www.eia.gov/electricity/930-content/about.html) specifies hour-ending values. The complete response has 1,488 records: 744 hours × two fuels, on exactly the same Pacific-January support as CAISO. Retain all reported values, including **382 negative net-solar hours**; do not clip them to mimic CAISO's zero nighttime values. Request parameters, retrieval date and response/route hashes are [recorded](../results/tables/generation_source_audit_metadata_2020_01.json). A public demo key was used; no user credentials or API request containing a private key are committed.

| Reported wind population | January energy |
| --- | ---: |
| EIA-930 CISO hourly sum | 1,002,027.000 MWh |
| CAISO raw five-minute archive, hourly aggregate | 991,545.496 MWh |
| EIA-923 reported CISO BA rows | 748,408.868 MWh |
| EIA-923 CA-state rows | 762,972.761 MWh |

EIA-930 wind is **1.0571%** above the CAISO raw total, with hourly correlation **0.9858**. EIA-930 solar totals 1,493,359 MWh, **4.1580%** below CAISO, with hourly correlation **0.9675**. These operational series are not independent plant-validation observations. Their close wind agreement does not reconcile either with EIA-923.

EIA-930 documents differences between operational and plant-survey populations and explains physical versus commercial accounting for dynamic transfers. These are reasons to examine source definitions, not evidence assigning the numerical discrepancy to a particular cause. No import adjustment, clipping or correction factor is applied. Use plant-matched EIA-923 energy for the diagnostic above, rather than forcing BA-wide output onto a statewide capacity denominator. See [all monthly source totals](../results/tables/generation_source_monthly_audit_2020_01.csv), [hourly source metrics](../results/tables/generation_source_hourly_metrics_2020_01.csv), and [paired operational observations](../data/processed/generation_source_hourly_audit_2020_01.csv).

## Reproduction and verification

Use the existing `requirements-wind.txt` environment. The matched-cohort CSVs are included; with the original wind and mask NetCDFs in their documented locations, run:

```bash
python scripts/13_bound_matched_wind_generation.py --headless
python -m unittest discover -s tests -v
```

Optional provenance reproduction uses separately acquired raw files and makes no automatic network request:

```bash
python scripts/12_match_january_wind_inventory.py --december-workbook /path/to/december_generator2019.xlsx --january-workbook /path/to/january_generator2020.xlsx --retrieved-on YYYY-MM-DD
python scripts/14_audit_generation_sources.py --eia930-response /path/to/eia930_ciso_january2020.json --eia930-route-metadata /path/to/eia930_route_metadata.json --retrieved-on YYYY-MM-DD
```

Use the actual source retrieval date. The optional `--wind-data` and `--mask` arguments allow reuse of existing raw files in other locations. All **56 tests** passed: the previous 42 plus 14 cohort, bounding and API-integrity checks. Independent original-workbook and array calculations verified the cohort, capacity/generation accounting, retirement dates, four power series, all 424 plant/curve bounds, 1,488 API values and saved metrics/hashes. See [verification evidence](january_wind_verification.json).

Next investigate wind representation at the highest-capacity sites and actual turbine/hub specifications before selecting or calibrating a model. Missing boundary weather can narrow these intervals but cannot close the observed shortfall under the current reference assumptions. Keep the source-population discrepancy open until asset-level reporting differences can be established.
