# Python environment

## Recorded working setup

The author reported this snapshot from the active Spyder IPython console after successfully running the January pilot:

- macOS on Apple Silicon (osx-arm64).
- Python **3.11.11**, as reported by `sys.version`.
- Direct package versions recorded in [`requirements.txt`](../requirements.txt).
- Spyder's project interpreter was previously verified as `/opt/anaconda3/envs/California_Reanalysis/bin/python3.11`.
- The updated Spyder application successfully connected using `spyder-kernels` **3.1.7**.

The earlier handoff listed Python 3.11.18. The latest console report is 3.11.11; this document records the observed value without assuming the cause of the difference.

The requirements file pins seven direct dependencies. It does not lock transitive dependencies, compiled-library builds, or the operating system. The author's original environment was not exported or independently reconstructed during repository review. Package pin syntax was validated; availability and installation of these exact versions in a new environment have not been checked here.

## Existing working environment

No environment reinstall is needed to continue using the working Mac setup. Keep existing ERA5 inputs and use the [documented script order](../README.md#local-workflow).

Spyder and its kernel are development tools, separate from the scientific runtime dependencies. They are deliberately omitted from the requirements file. The appropriate `spyder-kernels` version depends on the Spyder application being used; the successful 3.1.7 setup applies to the updated application in this project session.

## Recreate in a separate environment

The following is a proposed clean-install procedure, not a command already validated in this review. Run from the repository root with Conda available:

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

Then run the scripts in the README's order. The January reference checks are 695 selected grid centers, 743 aligned hourly intervals, and 31 observed trial low-resource periods including one start-boundary period. The full ERA5 workflow has been reported working by the author, but has not been rerun in the review workspace because the NetCDF inputs were not supplied.
