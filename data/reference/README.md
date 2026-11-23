# Scientific reference data

This directory contains small, versioned reference inputs, not ERA5 raw data.

- `wind_curves/`: three WTK normalized onshore curves, source YAML specifications, BSD license, immutable upstream commit and checksum manifest. No source CSV or specification was edited.
- `eia2020_ca_wind_generators.csv`: 117 retained California onshore operating-generator records from EIA-860 2020.
- `eia2020_ca_wind_plants.csv`: 101 plant points, aggregating 5,916.5 MW of wind nameplate capacity.
- `eia2020_ca_wind_exclusions.csv`: five out-of-service rows excluded from the reference layout, with explicit reasons.
- `eia2020_ca_wind_metadata.json`: source URL, archive/member hashes, selection rules, derived-file hashes, and quality checks.

The EIA snapshot describes end-of-2020 status and is held fixed as a location experiment, not actual January 2020 availability. The generic curves use 100 m wind; reported turbine heights differ. See [the full source and method documentation](../../docs/wind_assessment.md) and [research log](../../docs/research_log.md). Downloaded ZIP/XLSX files are not committed.
