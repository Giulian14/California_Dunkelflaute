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
