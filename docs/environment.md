# Python environment

## Recorded working setup

The author reported this snapshot from the active Spyder IPython console after successfully running the January pilot:

- macOS on Apple Silicon (osx-arm64).
- Python **3.11.11**, as reported by `sys.version`.
- Direct package versions recorded in [`requirements.txt`](../requirements.txt).
- Spyder's project interpreter was previously verified as `/opt/anaconda3/envs/California_Reanalysis/bin/python3.11`.
- The updated Spyder application successfully connected using `spyder-kernels` **3.1.7**.

The earlier handoff listed Python 3.11.18. The latest console report is 3.11.11; this document records the observed value without assuming the cause of the difference.

The requirements file pins seven direct dependencies. It does not lock transitive dependencies, compiled-library builds, or the operating system. A separate clean Python 3.11.11 environment was created on Linux x86_64, all seven pinned package versions installed successfully, and `pip check` passed. The complete January analysis was then rerun from the supplied ERA5 files. See the [full verification](full_workflow_verification.md) and [resolved Linux package snapshot](validated_linux_packages.txt). This reproduces the direct runtime versions and analysis, not the author's complete macOS/Conda installation.

## Existing working environment

No environment reinstall is needed to continue using the working Mac setup. Keep existing ERA5 inputs and use the [documented script order](../README.md#local-workflow).

Spyder and its kernel are development tools, separate from the scientific runtime dependencies. They are deliberately omitted from the requirements file. The appropriate `spyder-kernels` version depends on the Spyder application being used; the successful 3.1.7 setup applies to the updated application in this project session.

## Recreate in a separate environment

The following Conda-based procedure creates a separate environment. The successful automated verification used a Python 3.11.11 virtual environment on Linux rather than these Conda commands. Run from the repository root with Conda available:

```bash
conda create --name California_Dunkelflaute_Reproduce --override-channels -c conda-forge python=3.11.11 pip
conda activate California_Dunkelflaute_Reproduce
python -m pip install -r requirements.txt
python -m pip check
```

This keeps the reconstruction separate from the author's working `California_Reanalysis` environment. A successful install and `pip check` would establish dependency consistency; rerunning the analysis is still needed to validate scientific outputs.

The analysis requires the two existing ERA5 NetCDF files in `data/raw/`. The boundary GeoJSON is included in the repository. Skip `01_download_era5.py` when the data already exist; its original request is preserved for reference. No Copernicus credentials are required to run the analysis on existing files. `cdsapi` is included only because the repository also contains that original acquisition script.

## Verification after installation

```bash
python -c "import numpy, pandas, xarray, netCDF4, matplotlib, shapely, cdsapi; print('Scientific libraries loaded successfully.')"
```

Then run the scripts in the README's order. The January reference checks are 695 selected grid centers, 743 aligned hourly intervals, and 31 observed trial low-resource periods including one start-boundary period. The full ERA5 workflow has now also completed successfully in the clean Linux environment. Both final result tables match exactly; small wind capacity-factor differences are documented in the full verification report. This confirms computational reproducibility of the preliminary workflow, not validation of its physical assumptions.

## Optional PV generation extension

The original seven-package `requirements.txt` snapshot is preserved. `requirements-pv.txt` includes it and adds **pvlib 0.16.1**. A separate clean Python 3.11.11 Linux environment installed this extension, passed `pip check`, passed all 10 PV tests, and completed the January baseline and 25°/45° tilt scenarios. Resolved versions are recorded in [the PV Linux package snapshot](validated_pv_linux_packages.txt).

```bash
python -m pip install -r requirements-pv.txt
python -m unittest discover -s tests -v
python scripts/07_pv_capacity_factor.py --headless
```

These commands are intended for an environment with the model dependencies available; the assistant has not installed the extension on the author's Mac. Keep Spyder's application and kernel version requirements separate from the scientific runtime.

## Event-comparison extension

`08_compare_event_definitions.py` and its helper `energy_events.py` operate on the included processed CSVs and metadata. They require no additional dependencies beyond the original pilot runtime. They do not rerun PV modeling or access Copernicus. The complete test suite now contains 22 passing tests (12 event tests plus 10 PV tests), executed in the clean Python 3.11.11 PV environment. Running the complete suite requires `requirements-pv.txt`; the event-only suite can be run using `python -m unittest discover -s tests -p 'test_energy_events.py' -v`.

## Wind assessment and EIA inventory preparation

`requirements-wind.txt` includes the PV requirements and adds openpyxl **3.1.5** for reading the EIA source workbooks. A separate clean Python 3.11.11 Linux environment passed `pip check`, all **33 tests**, and the January wind assessment. [Resolved packages](validated_wind_linux_packages.txt) are recorded.

`09_assess_wind_model.py` uses the committed small reference tables and existing local ERA5 wind/mask files. It makes no network request. `00_prepare_eia_wind_inventory.py` is an optional provenance-reproduction step requiring a separately downloaded EIA-860 ZIP. The original environment snapshots are retained.

## Observed-generation benchmark

The November 23 observation extraction and comparison reused the existing wind environment and installed no additional packages. `requirements-wind.txt` supplies openpyxl for CAISO/EIA workbooks; `11_compare_observed_shapes.py` can instead use the committed CSVs. All **42 tests** and `pip check` passed. The nine new tests cover Pacific market-hour interpretation, UTC end labeling, energy conservation, missing/partial-hour rejection, complete local days and dimensionless shape metrics. Import intentionally supports January 2020 only; multi-month/DST handling remains future work.

## Matched January wind follow-up

Scripts 12–14 and `january_wind.py` reuse the existing wind environment and install no new dependencies. All **56 tests** pass (42 earlier + 14 cohort/bounds/API tests). Source workbooks, API JSON and route metadata are explicit file arguments; no script makes a network request. The matched model reuses the existing ERA5 wind and mask, with optional file-path overrides. No credentials are required to run it using the committed reference cohort and local weather inputs.
