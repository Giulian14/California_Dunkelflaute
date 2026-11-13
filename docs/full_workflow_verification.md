# Full January 2020 workflow verification

## Outcome

All seven analysis scripts completed successfully from the author's supplied ERA5 NetCDF inputs and the committed Census boundary, in a separate clean **Python 3.11.11** environment on **Linux x86_64**. All seven direct package versions matched `requirements.txt`, and `pip check` reported no broken requirements. The source workflow was originally run on macOS Apple Silicon, so operating-system and transitive binary builds differ.

The scripts were copied unchanged into a temporary project and run in this order:

```text
02_inspect_era5.py
02b_build_california_mask.py
03_california_averages.py
04_wind_capacity_factor.py
05_solar_resource_proxy.py
05b_align_hourly_resources.py
06_detect_trial_periods.py
```

Plotting used the noninteractive Matplotlib Agg backend. The original download script was not run, and no new ERA5 request was made.

## Input and output checks

- Both raw files contain 744 consecutive January 2020 UTC timestamps on the expected 41 × 45 grid. All expected wind, temperature, and radiation values are finite.
- The rebuilt California mask has 695 selected centers and exactly matches the uploaded mask's values and coordinates.
- Weather averages and the solar proxy reproduce the saved series within relative and absolute tolerances of 1e-12.
- Wind capacity factor has a maximum absolute difference of approximately **1.73e-9**; the aligned hourly wind approximation differs by at most **1.37e-9**. These small differences are consistent with floating-point evaluation of the float32 turbine curve across platforms. They pass a relative tolerance equal to float32 machine epsilon (approximately 1.19e-7), with absolute tolerance 1e-12.
- There are **zero changed hourly threshold classifications**. The nearest wind value to the 0.20 threshold is about 0.000301 away, substantially larger than the numerical differences.
- Both regenerated result tables exactly match the committed tables: **743 aligned intervals, 545 low-resource hours, 31 observed periods, 30 fully observed periods**, and a longest observed duration of **19 hours**. No observed period reaches 24 hours; the initial boundary-touching period's full duration remains unknown.
- All six expected figure files were generated and passed PNG-integrity checks. Pixel-equivalent rendering across operating systems is not asserted.

Original uploaded CSVs and PNGs were preserved. Raw NetCDF files and the generated NetCDF mask remain excluded from Git.

## Records and reproducibility limits

[Machine-readable verification](full_workflow_verification.json) includes input SHA-256 checksums, variable ranges and units, package versions, per-column numerical differences and tolerances, threshold margins, and script exit codes. [Installed Linux packages](validated_linux_packages.txt) records the resolved Python package versions for this run; it is not a platform-independent or fully hashed environment lockfile.

This establishes computational reproducibility of the January pilot. It does not establish that the illustrative turbine, solar proxy, spatial weighting, or trial thresholds are adequate final scientific models. The administrative mask includes state waters, uniform capacity weighting does not represent the actual fleet, and ordinary nighttime conditions strongly affect the trial low-resource periods.
