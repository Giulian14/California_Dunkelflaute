# Wind-site and annual-capacity diagnostics

On November 23, 2026, an additional audit found that the earlier monthly-snapshot match was insufficient to establish fully comparable plant capacities. This report narrows that cohort and tests spatial wind sampling. It supersedes the 106-plant cohort as the most conservative available comparison; earlier numerical artifacts are retained as conditional results, with a caveat added to their report.

## Annual capacity cross-check

Reused the preserved official EIA-860 2020 ZIP and its two wind sheets (`Operable`, `Retired and Canceled`) plus plant coordinates. Joined the 123 January generator records by plant and generator ID; all had annual records and reported heights. Three generator capacities disagree with the annual file:

| Plant | Generator | January MW | Annual MW |
| --- | --- | ---: | ---: |
| 50821, Mojave 16 | GEN1 | 48.0 | 88.5 |
| 52142, Mojave 4 | GEN1 | 29.0 | 75.0 |
| 55719, Mountain View I&2 | GENI | 44.4 | 42.6 |

The 40.5 MW increase at Mojave 16 equals the January capacity of unmatched Mojave 18. The 46 MW increase at Mojave 4 equals the combined January capacities of unmatched Mojave 3 and Mojave 5. This is evidence to investigate reporting consolidation; it is **not** an established asset-ID crosswalk. Annual EIA-923 plant records may not represent the same generator population as a January inventory carrying those plant IDs. Do not infer a merge or assign their generation by guessed fractions.

Exclude every whole plant containing a missing annual generator match or any capacity disagreement greater than 1e-6 MW. Mountain View's other 22.2 MW unit is excluded with its plant. The resulting **capacity-consistent subset** has **103 plants / 119 generators / 5,842.1 MW**, with **735,337.752 MWh** and observed nominal monthly CF **0.16917841**. Agreement of reported capacities still does not establish full asset lineage, true hourly availability, or January identity of the predominant annual turbine equipment.

The [generator audit](../data/reference/jan2020_wind_annual_turbine_audit.csv) retains all 123 original records and flags whole-plant eligibility. The [new subset](../data/reference/jan2020_wind_capacity_consistent_plants.csv) is separate from previous inventories. Heights/models are descriptive end-2020 reports; do not silently use them as confirmed January turbine configurations or calibrate a height adjustment to the generation totals.

## Coordinates, units and interpolation

All **106** original plant coordinates match the annual plant file. Their maximum separation is **0.00413 km**, about four metres. These sources may share underlying records, so agreement is not independent confirmation of turbine micrositing. Distance from a monthly plant point to its nearest ERA5 center has median **10.44 km** and maximum **17.13 km** across those 106 sites.

Verified finite 100 m u/v fields in m/s, the source's unrotated-grid flag, monotonic grid axes and consecutive UTC hours. For nearest sampling, preserve file-order tie handling. For bilinear sampling, interpolate **u and v separately at the plant point**, then compute magnitude and apply the power curve. Do not interpolate cell power factors or average speed magnitudes. Convert snapshots to preceding-hour CF once by endpoint averaging; spatial capacity shares have no extra latitude factor.

The 119 retained generators all have positive reported annual hub heights. Their January-capacity-weighted mean is **73.81 m**. This identifies a mismatch with the controlled 100 m wind reference, but no vertical extrapolation is performed: actual January configurations and a defensible shear model remain unverified. No ERA5 surface geopotential/orography or turbine-level/met-mast wind reference was acquired in this stage. Terrain remains a hypothesis to investigate, not an established explanation.

## Results

Retain the same four curves, monthly capacity denominator and nine-missing-hour CF 0–1 bound. No gain, curve parameter or threshold is fitted. The observed nominal CF for this subset is **16.92%**.

| Curve | Nearest-center monthly CF bounds | Bilinear-vector monthly CF bounds |
| --- | ---: | ---: |
| Cubic | 5.70%–6.91% | 4.98%–6.19% |
| WTK IEC I | 7.39%–8.60% | 6.51%–7.72% |
| WTK IEC II | 9.85%–11.06% | 8.68%–9.89% |
| WTK IEC III | 12.47%–13.67% | 11.06%–12.27% |

For IEC II, even the nearest-center upper energy bound is **480,524.005 MWh**, at least **34.65%** below observed energy. Bilinear sampling's upper bound is **429,922.940 MWh**, at least **41.53%** below. Excluding the ambiguous capacities does not remove the shortfall; bilinear interpolation does not resolve it. Neither method adds subgrid terrain information, and closeness to a monthly energy total alone is not an accuracy ranking.

The [site diagnostics](../results/tables/wind_site_iec2_diagnostics_2020_01.csv) identify where to investigate first. Voyager Wind II and Tule Wind have the largest positive nearest-center IEC II residuals against the missing-hour upper bound, followed by Shiloh I and Shiloh 2. These are prioritization results, not diagnoses of those sites. Inspect actual turbines, plant footprint, terrain and independent wind information before fitting corrections.

See [all eight sampling/curve cases](../results/tables/wind_site_sampling_bounds_2020_01.csv), [735-hour series](../data/processed/wind_site_sampling_2020_01.csv), [coordinate audit](../results/tables/wind_site_coordinate_audit_2020_01.csv), [figure](../results/figures/wind_site_sampling_bounds_2020_01.png), and [metadata](../results/tables/wind_site_diagnostic_metadata_2020_01.json).

## Reproduce and verify

Use the existing wind environment, original January wind NetCDF and previously downloaded EIA-860 ZIP:

```bash
python scripts/15_diagnose_wind_sites.py --eia860-archive /path/to/eia8602020.zip --headless
python -m unittest discover -s tests -v
```

An optional `--wind-data` path reuses raw inputs outside the repository. This script downloads nothing and installs no packages. All **63 tests** passed. Independent annual-record joins reproduced the three excluded plants and 119-generator subset; manual four-corner u/v interpolation and independent curve calculations checked all eight time series and all 206 IEC II plant/sampling cases. New nearest-sampling bounds agree with aggregation of the earlier per-plant bounds for the same subset. Source and output hashes are retained in [verification](wind_site_verification.json).

The [expansion-readiness record](expansion_readiness.md) separates verified pilot mechanics from the unresolved scientific checks needed for 2005–2024.
