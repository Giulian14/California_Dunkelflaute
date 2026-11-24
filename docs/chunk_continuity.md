# Weather-file and event continuity verification

Completed November 24, 2026. This stage verifies processing mechanics using the existing January 2020 ERA5 pilot and explicitly synthetic calendar cases. It does not add adjacent-month observations, change physical models or establish 2005–2024 event frequencies.

## Architecture

Read weather one file pair at a time, retain only its final instantaneous/accumulated record for the next bracket, and calculate complete-hour resource means. Keep those compact means in chronological order, join them, and then run the existing rolling-window and event algorithms globally. The two-resource float64 values for 175,320 hours occupy about **2.8 MB**, excluding index/processing overhead; the large gridded weather arrays do not need to be held for 20 years at once.

```mermaid
flowchart LR
    A[Ordered weather file pairs] --> B[Carry one preceding snapshot]
    B --> C[Model each cell and complete hour]
    C --> D[Spatially aggregate resource means]
    D --> E[Join compact hourly series]
    E --> F[Global rolling windows and event unions]
```

The helper [continuous_resources.py](../scripts/continuous_resources.py) provides the reusable weather iterator, preserved model block and compact-series join. Inputs must be consecutive, ordered and nonoverlapping. Reject gaps, duplicate boundaries, changed spatial grids, changed field units/dtypes, nonfinite required forcings and invalid resource values; do not sort, deduplicate, interpolate gaps or fill missing generation with zero. Resource indices must be timezone-aware; aware local labels are converted to UTC. Ambiguous naive local labels are rejected.

The globally initial snapshot provides a bracket. Its preceding interval is unavailable unless an earlier snapshot was supplied. This is handled **once for the entire sequence**, rather than dropping an hour from every file. A first file with just one snapshot is retained until the next input supplies a complete interval. Carrying a preceding ssrd record is for alignment only: the next interval uses its own end-labeled hourly accumulation, with no temporal smoothing of irradiance or modeled PV. Wind CF snapshots and bracketing temperature are averaged once. The ERA5 hourly accumulation semantics must already be established; this code does not infer forecast or ERA5-Land deaccumulation rules.

## Real January experiment

Using the original 744-timestamp, 41 × 45-grid input files and 695-cell mask, reran the unchanged illustrative cubic/uniform wind model and fixed-tilt 35° PV model. Modeling remained cell-by-cell before spatial averaging. The continuous reference agrees with archived wind CF within **1.67 × 10⁻¹⁶** and archived PV exactly. New outputs are separate from the preserved pilot/scenario artifacts.

Wrote temporary NetCDF file pairs containing identical decoded physical values, then reopened them through the new reader. The temporary files were removed after verification.

| Case | Snapshot partition boundaries | Complete output hours | Maximum GHI difference | Maximum temperature difference | Maximum wind CF difference | Maximum PV CF difference |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Two files | 0, 500, 744 | 743 | 0 | 0 | 4.34e-19 | 0 |
| Six irregular files | 0, 1, 25, 169, 481, 743, 744 | 743 | 0 | 0 | 2.78e-17 | 0 |

The irregular case includes one-record initial and final files. All selected-cell forcing arrays were checked against the continuous calculation, not just statewide averages. Both cases preserve the same 743 interval-end labels, January 1 at 01:00 UTC through January 31 at 23:00 UTC. Equality tolerance for numerical CF comparisons was 1e-12; recorded differences are much smaller and change no event classifications.

Compared the strict simultaneous hourly reference and nine combinations of wind share (0.25, 0.50, 0.75) and combined 48-hour threshold (0.05, 0.06, 0.10) for each partition: **18 rolling-window comparisons**. All diagnostic values, event timestamps, durations, qualifying-window counts and boundary flags match the continuous reference. Both retain **502 simultaneous low hours**, **31 periods**, and **zero ≥24-hour periods** under the existing strict definition.

### Deliberately incorrect per-file control

At 75% wind and threshold 0.06, the joined series preserves the existing **one 199-hour window-support union**. Detecting events independently in each file demonstrates a failure:

| Method | Event records | Sum of covered union hours |
| --- | ---: | ---: |
| Continuous/joined calculation | 1 | 199 |
| Naive two-file calculation | 2 | 199 |
| Naive six-file calculation | 2 | 186 |

The two-file control splits one period into two records; the irregular control also loses 13 hours because rolling context is reset. Summing independently generated catalogues is therefore insufficient. These are conditional modeled window unions, not 199 consecutive hours below the threshold or newly observed generation events.

See [weather comparisons](../results/tables/continuity_weather_checks_2020_01.csv), [rolling checks](../results/tables/continuity_event_checks_2020_01.csv), [hourly checks](../results/tables/continuity_hourly_reference_checks_2020_01.csv), and the three separately named compact resource CSVs under `data/processed/continuity_*_resources_2020_01.csv`.

## Synthetic calendar controls

Constructed three controlled 216-hour sequences, with both resource values equal to 0.5 except for an internal 72-hour block at 0.01. Split them by UTC calendar month and rejoin them. These values are test fixtures, not realistic radiation observations or observed Dunkelflauten.

| Calendar | Strict low-period support | Joined strict duration | Joined 48h-window union duration | Qualifying windows | Naive independent union duration |
| --- | --- | ---: | ---: | ---: | ---: |
| New Year | Dec 31, 2019–Jan 3, 2020 | 72 h | 80 h | 33 | 53 h |
| Leap February | Feb 29–Mar 3, 2020 | 72 h | 80 h | 33 | 53 h |
| Nonleap February | Feb 28–Mar 3, 2019 | 72 h | 80 h | 33 | 53 h |

Supporting windows extend four hours either side of the 72-hour low block, so the union is 80 hours; not every hour in that union has low output. Each correctly joined synthetic event has complete outer context. Additional unit checks preserve all 24 UTC leap-day hours, convert aware spring/fall Pacific DST labels into unique consecutive UTC instants, and reject naive local labels. These DST checks do not generalize the January-only CAISO observation importer.

See [calendar checks](../results/tables/continuity_synthetic_calendar_checks.csv) and [explicitly labeled synthetic event times](../results/tables/continuity_synthetic_events.csv).

## Reproduction and verification

Reuse the original inputs; no downloads, credential changes or new dependencies are needed. The current full suite uses the previously established terrain environment:

```bash
python -m pip install -r requirements-terrain.txt
python -m unittest discover -s tests -v
python scripts/18_verify_chunk_continuity.py --session-date YYYY-MM-DD
```

Supply the actual verification date. Optional `--instant`, `--accum` and `--mask` arguments reuse raw files at other paths. The validation driver is deliberately specific to the 744-snapshot January pilot; the reusable iterator does not impose that length.

All **85 tests** passed: 72 earlier plus 13 continuity checks. Independent handwritten wind calculations and archived PV regression verified the reference; independent direct-slice rolling means, support unions and run extraction verified all 18 cases. Event timestamps, durations, window counts and censoring flags agreed with the preserved earlier baseline catalogue. Independent calculations also reproduced the deliberately incorrect controls and all three synthetic cases. See [run metadata](../results/tables/continuity_metadata_2020_01.json) and [verification evidence](continuity_verification.json).

## Remaining limits before production

This closes the tested algorithmic file-boundary issue for the known data format. Real contiguous multi-month inputs, changes in source conventions/version metadata, acquisition resumption and full-scale performance still need a rehearsal. A future resumable runner must supply the preceding bracket when restarting and verify matching model configuration/provenance; the helper is not a complete checkpointing scheduler.

For a UTC `[2005-01-01 00:00, 2025-01-01 00:00)` core, the correct count is **175,320 intervals**, including 120 hours on five leap days. Hourly end labels run from January 1, 2005 at 01:00 through January 1, 2025 at 00:00. Obtain both endpoint samples and explicit outside-core window/event context. Cropping to the study core also requires a defined event-inclusion rule; do not silently truncate an event and present it as fully observed. The existing outer-boundary flags remain necessary even when internal file joins are correct.

Physical wind bias, asset lineage, PV amplitude, held-out-period validation and final event/temperature definitions remain open. This is computational continuity evidence, not physical validation or a 20-year climatology.
