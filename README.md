# California Dunkelflaute Research

Graduate project for EN 530.637 — Energy Meteorology, Johns Hopkins University.

## Research question

How frequently do prolonged periods of low wind and solar energy availability occur in California, and how often do they coincide with temperature extremes?

The intended study period is **2005–2024**. Current work is a **January 2020 pilot**, not a completed climatological analysis.

## Current status

The pilot workflow has been run successfully on the author's Mac using Python 3.11, Anaconda, and Spyder. It opens existing ERA5 files, builds a California mask, calculates weather averages, estimates preliminary resource indicators, and detects trial low-resource periods.

**The eight uploaded Python scripts are now in `scripts/`, preserved unchanged from the author's archive.** The exact California boundary file is included in `data/boundaries/`, with [source and checksum documentation](docs/boundary_provenance.md). The [six pilot figures and two result tables](results/README.md) are also included, with file checksums and review notes. The reported Python 3.11.11 package versions are recorded in [`requirements.txt`](requirements.txt), with [environment setup and verification notes](docs/environment.md). This is a direct-dependency snapshot, not a complete environment lockfile.

All eight scripts passed syntax checks. Synthetic-data checks passed for hourly alignment, empty detections, a 30-hour internal period, start/end boundary flags, an all-low window, and rejection of missing timestamps. The [saved processed CSVs](data/processed/README.md) are now included. Rerunning alignment and detection from those inputs reproduced both final result tables exactly, including 545 low-resource hours, 31 periods, and 30 fully observed periods. This verifies the saved-series-to-results stage; the underlying ERA5-to-resource models have not been rerun here because their raw NetCDF inputs were not supplied.

## Data

- [ERA5 hourly data on single levels](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels), Copernicus Climate Data Store.
- January 1–31, 2020, hourly, in UTC.
- Bounding box: north 42°, west −125°, south 32°, east −114°.
- Variables: 100 m wind components (`u100`, `v100`), 2 m temperature (`t2m`), and surface solar radiation downwards (`ssrd`).
- Grid: 41 latitudes × 45 longitudes, with 744 hourly timestamps.
- California boundary: U.S. Census Bureau TIGERweb, 2026 vintage, selected using GEOID 06 and exported in longitude/latitude coordinates.

The existing download was a ZIP archive despite its .nc filename. Its extracted files are:

```text
data_stream-oper_stepType-instant.nc
data_stream-oper_stepType-accum.nc
```

The administrative mask selects **695 grid centers** inside or on California's boundary. It includes state waters and is not a land-only mask.

Raw NetCDF files and credentials are excluded from Git. No additional ERA5 download is needed to rerun the pilot on the existing local data.

## Preliminary methods

1. Wind speed: sqrt(u100² + v100²), in m/s.
2. Temperature: t2m − 273.15, in °C.
3. For this hourly CDS ERA5 product, ssrd / 3600 gives preceding-hour mean irradiance in W/m².
4. Spatial averages use cosine-of-latitude area weights.
5. Illustrative wind capacity factors use a cubic curve between cut-in at 3 m/s and rated output at 12 m/s, full output below cut-out at 25 m/s, and zero outside the operating range.
6. The solar resource proxy is irradiance / 1000 W/m², clipped to 0–1. It is **not a full photovoltaic capacity-factor model**.
7. Resource conversion occurs at each grid cell before spatial averaging, representing hypothetical capacity distributed uniformly per unit area within the mask.
8. Adjacent instantaneous wind capacity factors are averaged to approximate preceding-hour values. This assumes linear changes between snapshots; it is not an observed hourly generation average.
9. The first interval lacks the preceding wind snapshot and is excluded, leaving **743 hourly intervals**.
10. Trial low-resource periods require both normalized values to be strictly below 0.20. Minimum-duration sensitivity is evaluated at 6, 12, 18, 24, and 48 hours. Periods touching data boundaries are flagged.

## Pilot results

| Metric | January 2020 |
| --- | ---: |
| Illustrative wind capacity factor, monthly mean over 744 snapshots | 0.047 |
| Solar resource proxy, monthly mean over 744 hours | 0.116 |
| Hours meeting both trial thresholds | 545 of 743 |
| Observed uninterrupted low-resource periods | 31 |
| Fully observed periods | 30 |
| Longest observed low-resource duration | 19 hours |
| Observed periods reaching 24 hours | 0 |

One period touches the start of the available intervals. Its observed 17-hour duration is a lower bound; its full duration is unknown. Most observed periods last 17–18 hours, suggesting a strong influence from the day–night cycle.

**These results do not establish California's Dunkelflaute frequency or the absence of longer events outside the observed window.**

## Local workflow

To reproduce the event tables directly from the included processed series, run from the repository root:

```bash
python scripts/05b_align_hourly_resources.py
python scripts/06_detect_trial_periods.py
```

These two steps do not require raw ERA5 files or API credentials. See the [processed-data notes](data/processed/README.md) for units, verification scope, and the legacy sensitivity diagnostic.

For the full workflow using existing raw ERA5 inputs:

Skip `01_download_era5.py` when using the existing data. It is retained as the original request record, contains a Mac-specific output path, and starts a CDS request when executed or imported. It does not extract the ZIP response. The analysis scripts use paths relative to the project directory.

Run scripts in this order once the input files are available locally:

```text
scripts/02_inspect_era5.py
scripts/02b_build_california_mask.py
scripts/03_california_averages.py
scripts/04_wind_capacity_factor.py
scripts/05_solar_resource_proxy.py
scripts/05b_align_hourly_resources.py
scripts/06_detect_trial_periods.py
```

Inputs belong in `data/raw/`, with the saved Census GeoJSON in `data/boundaries/`. Derived files go to `data/processed/`; figures and tables go to `results/figures/` and `results/tables/`.

The local workflow produces maps, time series, and a duration histogram.

## Remaining work

- Replace or assess the illustrative turbine curve and implement a defensible photovoltaic model.
- Assess land filtering and capacity-location weighting.
- Establish a final event definition that accounts for ordinary nighttime conditions, seasonality, and model uncertainty.
- Extend the validated workflow to 2005–2024.
- Analyze temperature extremes, meteorological mechanisms, and threshold sensitivity.

Temperature is a demand proxy. Actual load and electricity-system data would be needed to quantify electricity shortfalls; a meteorological renewable-energy drought is not automatically an electricity shortage.
