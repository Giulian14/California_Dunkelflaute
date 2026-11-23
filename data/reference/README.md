# Scientific reference data

This directory contains small, versioned reference inputs, not ERA5 raw data.

- `wind_curves/`: three WTK normalized onshore curves, source YAML specifications, BSD license, immutable upstream commit and checksum manifest. No source CSV or specification was edited.
- `eia2020_ca_wind_generators.csv`: 117 retained California onshore operating-generator records from EIA-860 2020.
- `eia2020_ca_wind_plants.csv`: 101 plant points, aggregating 5,916.5 MW of wind nameplate capacity.
- `eia2020_ca_wind_exclusions.csv`: five out-of-service rows excluded from the reference layout, with explicit reasons.
- `eia2020_ca_wind_metadata.json`: source URL, archive/member hashes, selection rules, derived-file hashes, and quality checks.

The EIA snapshot describes end-of-2020 status and is held fixed as a location experiment, not actual January 2020 availability. The generic curves use 100 m wind; reported turbine heights differ. See [the full source and method documentation](../../docs/wind_assessment.md) and [research log](../../docs/research_log.md). Downloaded ZIP/XLSX files are not committed.

## January-specific wind matching

`dec2019_ca_wind_snapshot.csv` and `jan2020_ca_wind_snapshot.csv` preserve CA wind records extracted from the official monthly Operating sheets, including non-OP statuses and source row numbers. `jan2020_wind_generator_transition.csv` and `jan2020_wind_retirements.csv` document changes and reported retirement months. `jan2020_wind_plant_audit.csv` retains every plant-level inclusion/exclusion; `jan2020_wind_matched_plants.csv` and `jan2020_wind_matched_generators.csv` define the conservative 106-plant, 123-generator, 5,985.7 MW cohort. Checksums and rules are in `jan2020_wind_inventory_metadata.json`. These are separate from the preserved fixed end-2020 scenario. See [method](../../docs/january_wind_match.md).

## Annual-capacity consistency refinement

`jan2020_wind_annual_turbine_audit.csv` joins all 123 original generators to annual wind records, retaining capacity-consistency/whole-plant flags, source sheet/row and reported predominant equipment. `jan2020_wind_capacity_consistent_plants.csv` defines the more conservative 103-plant, 119-generator, 5,842.1 MW subset. Three whole plants are excluded for capacity disagreement; no reporting-consolidation alias is inferred. This refines, rather than overwrites, the previous monthly-snapshot cohort. See [latest interpretation](../../docs/wind_site_diagnostics.md).
