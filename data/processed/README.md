# Saved January 2020 processed data

The five CSV files here are preserved unchanged from the author's uploaded `processed.zip`. They were generated locally from the ERA5 single-levels data and California administrative mask described in the [project README](../../README.md). All times are UTC, stored as timezone-naive strings.

## Files and units

| File | Rows | Contents |
| --- | ---: | --- |
| `california_hourly_weather_2020_01.csv` | 744 | `time_utc`; `wind_speed` in m/s; `temperature_c` in degrees Celsius; `irradiance` in W/m² |
| `illustrative_wind_cf_2020_01.csv` | 744 | `time_utc`; dimensionless `wind_capacity_factor` from the illustrative turbine curve |
| `solar_resource_proxy_2020_01.csv` | 744 | `time_utc`; dimensionless `solar_resource_proxy`, not full photovoltaic capacity factor |
| `preliminary_hourly_resources_2020_01.csv` | 743 | `interval_end_utc`; `wind_cf_hourly_approx`; `solar_resource_proxy` |
| `trial_duration_sensitivity_2020_01.csv` | 5 | Legacy diagnostic with minimum duration and `qualifying_periods` |

The wind snapshots and temperature are instantaneous at their timestamps. Irradiance and the solar proxy describe the preceding hour. The aligned file approximates preceding-hour wind capacity factor by averaging adjacent snapshots and excludes the first interval because its prior wind snapshot is unavailable. Its timestamps run from January 1 at 01:00 to January 31 at 23:00, 2020.

Values are area-weighted across the 695 selected administrative-area grid centers, including state waters. Resource models assume uniformly distributed capacity per unit area; they do not represent California's actual generation fleet.

## Final sensitivity table versus legacy diagnostic

The legacy `trial_duration_sensitivity_2020_01.csv` in this directory records the earlier console diagnostic. Its counts equal `all_observed_periods` in the final [boundary-aware sensitivity table](../../results/tables/trial_duration_sensitivity_2020_01.csv). Use that final table for reporting: it also distinguishes fully observed periods. The legacy CSV is retained for provenance and is not an input to the detection script.

## Reproduce the alignment and result tables

With the scientific dependencies available, run from the repository root:

```bash
python scripts/05b_align_hourly_resources.py
python scripts/06_detect_trial_periods.py
```

These two steps use the included CSVs and require neither the raw NetCDF inputs nor Copernicus credentials. They rewrite the aligned CSV, period catalogue, sensitivity table, and duration histogram. Floating-point formatting or plot rendering can differ between package versions.

Repository review reran both scripts using these supplied CSVs. The alignment matched the uploaded values within relative and absolute tolerances of 1e-12. Both regenerated result tables matched the supplied GitHub tables exactly. The checks reproduced 545 low-resource hours, 31 observed periods, and 30 fully observed periods. All expected hourly timestamps and finite numeric values were also checked. Review runtime versions and original-file checksums are recorded in [the verification record](../../docs/processed_verification.json).

These checks validate the saved-series-to-results stage. They do not independently verify the ERA5-to-resource calculations or a clean installation of the author's pinned environment.

The uploaded `california_mask.nc` is excluded from Git by the project's NetCDF rule. Recreate it with `02b_build_california_mask.py` using the committed boundary and existing ERA5 coordinate grid. The analysis does not treat the first truncated low-resource period's observed duration as its full duration.
