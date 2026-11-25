# Limited validation download after the paper review

Prepared November 25, 2026. This is a small staged request plan, **not a download already performed**, and does not authorize or implement a 2005–2024 retrieval. The cloud environment still lacks a configured CDS client. Use the author's existing private Copernicus setup locally; no API key needs to be shared in chat or committed.

The [paper comparison](paper_method_comparison.md) establishes why the next check needs more than the original four fields. These requests support a controlled conversion/validation comparison, not a claim to reproduce all of Mockert's weather-regime or demand analysis.

## Inputs and first stage

Reuse the existing January 2020 `u100`, `v100`, `t2m`, `ssrd` files. Request **only six missing January fields**:

| CDS variable | Role |
| --- | --- |
| `10m_u_component_of_wind`, `10m_v_component_of_wind` | Additional wind-height/shear diagnostic; also part of the inspected modern atlite wind input contract |
| `forecast_surface_roughness` | Roughness-aware wind-height comparison |
| `surface_net_solar_radiation` | Together with downwelling radiation, derive surface albedo |
| `toa_incident_solar_radiation` | Top-of-atmosphere input for the comparison conversion |
| `total_sky_direct_solar_radiation_at_surface` | Direct **horizontal** solar energy; not direct normal irradiance |

February 2020 and endpoint records include all ten variables (the original four plus six above). Diffuse horizontal energy is `ssrd − fdir`; albedo uses `(ssrd − ssr)/ssrd`. These require daylight/zero-denominator, physical-range and rounding checks, not blind clipping of missing data. Solar-position timing must remain consistent with preceding-hour accumulation; the inspected atlite source uses a −30-minute midpoint shift. Direct horizontal energy cannot be supplied as DNI without solar-geometry conversion. Existing Erbs/PVWatts results remain preserved for comparison.

| First-stage batch | Requested support | Fields |
| --- | --- | ---: |
| `winter_2020_01_extra` | January 1–31, hourly UTC | 6 supplemental only |
| `winter_2020_02` | February 1–29, hourly UTC | 10 |
| `winter_2020_end` | March 1, 00:00–08:00 UTC | 10 |

Together with the preserved January base files, this supplies **1,449 snapshots**, including the final support needed for complete UTC January/February and Pacific-month energy comparisons. The new first-stage float32 array values would occupy approximately **85 MB uncompressed**, excluding coordinates/metadata; actual downloads depend on compression and encoding. No values have yet been fetched, merged or validated. Merge only after exact coordinate/time and product-version checks. If existing/new data are incompatible, stop and inspect rather than silently splicing them.

Following-month records are intended to close the nine unavailable hours in the previous Pacific-January energy comparison. Endpoint padding for monthly energy does not supply all outside-edge 48-hour event context; retain event censoring and incomplete-context flags.

Later predeclared stages cover July 2020 for contrasting-season development, then January/July 2021 for held-out observed-generation evaluation. Each month includes nine UTC records on the following month's first day. Those cover UTC−8 winter and UTC−7 summer month ends, with one extra summer context hour. The nine-batch plan spans only these validation periods. It is separate from the earlier unsubmitted 242-request archive plan.

## Running locally

Use **the Mac's system Terminal**, from the project root, after updating the local scripts from GitHub. The new script needs `validation_download.py` and the existing `archive_preflight.py` in the same `scripts/` folder. It uses the already reported Python environment and `cdsapi`; no additional model package is needed for downloading.

Start with a preview, which does not authenticate or create download files:

```bash
/opt/anaconda3/envs/California_Reanalysis/bin/python3.11 \
  scripts/23_download_validation_batch.py --batch winter_2020_01_extra
```

Then download one explicit batch:

```bash
/opt/anaconda3/envs/California_Reanalysis/bin/python3.11 \
  scripts/23_download_validation_batch.py \
  --batch winter_2020_01_extra --download --output-dir data/raw/validation
```

After it finishes, use the same command for `winter_2020_02`, then `winter_2020_end`. There is deliberately no all-batch download switch. Leave later stages until the winter input checks and comparison are reviewed. No cloud-side request has been submitted during preparation, and the live CDS schema/response path still needs this first real execution check.

Each download produces a `.zip` and `.receipt.json` under the excluded raw-data directory. The script checks ZIP integrity and NetCDF member presence, records request/byte hashes and client version, and reuses only a matching completed receipt. It refuses to overwrite mismatched or partial outputs. The receipt explicitly says scientific NetCDF QC is **not yet run**. Preserve receipts with the files; both are needed for provenance. Archive integrity does not establish correct grid, accumulation semantics, coverage or model accuracy.

Generate the complete reviewable plan without downloading:

```bash
python scripts/23_download_validation_batch.py --session-date 2026-11-25 \
  --plan-output results/tables/limited_validation_download_plan.json
```

The four new tests cover January reuse, leap-month/boundary/holdout support, authentication-free planning and rejection of an unbounded download command. Actual network retrieval, scientific merge/QC, model comparison, matched additional-period observations and withheld scoring remain subsequent work.
