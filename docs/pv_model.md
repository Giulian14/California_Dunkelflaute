# Representative photovoltaic model

This extension estimates fixed-tilt PV **AC capacity factor** from the existing January 2020 ERA5 radiation and temperature files. It is a documented system scenario, not a reconstruction or observational validation of California's solar fleet. The original irradiance proxy and its event results remain available unchanged.

## Inputs and hourly conventions

- `ssrd`: preceding-hour accumulated solar energy in J/m²; divide by 3600 for global horizontal irradiance (GHI) in W/m².
- `t2m`: instantaneous air temperature in kelvin; average the snapshots bracketing each interval, then subtract 273.15.
- Existing 695-cell administrative mask, including state waters, with cosine-of-latitude area weights.

The first radiation interval lacks its preceding temperature snapshot. Exclude it, leaving **743 intervals** with UTC end labels from January 1 at 01:00 to January 31 at 23:00. Evaluate solar position 30 minutes before each end label, but retain the end label in the output. This follows pvlib's [guidance for interval averages](https://pvlib-python.readthedocs.io/en/stable/gallery/irradiance-transposition/plot_interval_transposition_error.html). Midpoint geometry is an approximation, especially around sunrise and sunset and during rapid cloud changes.

The new PV series already estimates preceding-hour output. **Do not apply another two-snapshot rolling average to it.** Subsequent wind/PV comparisons should align these labels with the existing preceding-hour wind approximation. The PV CSV writes explicit UTC offsets; localize the older timezone-naive wind labels to UTC before joining them.

## Baseline scenario

| Parameter | Assumption |
| --- | --- |
| Panel type | Monofacial, fixed tilt |
| Tilt / azimuth | 35° from horizontal / 180° (south) |
| Ground albedo | 0.20, constant |
| Cell temperature | Ross model, NOCT 45°C |
| DC temperature coefficient | −0.004 per °C relative to 25°C |
| Array DC / inverter AC rated capacity | 1.20 |
| Other system losses | 14%, applied once before the inverter |
| Nominal inverter efficiency | 96% |
| Spatial deployment | Equal AC capacity per unit area within the mask |

These are explicit representative parameters, not estimates fitted to January's event counts or California fleet data.

## Calculation at each grid cell

1. Calculate solar position with pvlib's NREL NumPy implementation, using true zenith and nominal sea-level altitude/pressure.
2. Estimate direct normal and diffuse horizontal irradiance from GHI using the [Erbs decomposition](https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.irradiance.erbs.html). These components are inferred, not measured ERA5 direct/diffuse inputs.
3. At midpoint zenith ≥87°, set direct irradiance to zero and assign GHI to diffuse irradiance. This preserves energy reported for partly sunlit intervals without an unstable low-sun direct beam. It does not claim the entire interval was dark. The baseline run attributes about **0.068%** of weighted GHI energy to intervals whose midpoint is below the geometric horizon; this diagnostic is recorded in metadata.
4. Apply [isotropic plane-of-array transposition](https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.irradiance.get_total_irradiance.html) to include beam, sky diffuse, and reflected contributions on the tilted panel.
5. Estimate cell temperature with [Ross](https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.temperature.ross.html): `T_cell = T_air + (NOCT − 20) / 800 * POA`. This model assumes nominal 1 m/s ventilation rather than using the ERA5 100 m wind speed as module-height wind.
6. Use [PVWatts DC](https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.pvsystem.pvwatts_dc.html), apply the other-loss fraction, then use the [PVWatts inverter](https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.inverter.pvwatts.html).

Normalize inverter rated AC power to 1 W. Array DC STC power is therefore 1.20 W, while the inverter function's `pdc0` is `1 / 0.96` W. The two pvlib parameters named `pdc0` have different meanings. Divide output by the 1 W AC rating; the resulting capacity factor is bounded by 0–1. Apply this chain **before spatial averaging**.

## January results and tilt sensitivity

All scenarios use the same 743 intervals, temperature model, losses, and capacity ratio.

| Tilt | Mean modeled AC CF | Maximum hourly area-average CF |
| --- | ---: | ---: |
| 25° | 0.158541 | 0.773699 |
| **35° baseline** | **0.169478** | **0.821202** |
| 45° | 0.176466 | 0.851464 |

The baseline's mean over the available intervals is **16.95%**. This is not directly interchangeable with the original GHI/1000 proxy: tilt changes incident radiation and the new denominator is rated AC power, with a specified DC/AC ratio. The tilt range is a scenario sensitivity, not a confidence interval or a general finding that 45° is optimal year-round.

## Run and verify

The original `requirements.txt` is preserved. The extension adds a separate dependency file:

```bash
python -m pip install -r requirements-pv.txt
python -m unittest discover -s tests -p 'test_pv_model.py' -v
python scripts/07_pv_capacity_factor.py --headless
```

Use a separate environment for installation if preserving an existing Spyder setup. The extension was installed and executed in a separate clean Python 3.11.11 Linux environment; installation on the author's Mac has not been performed by the assistant.

The default script reads the existing raw files and generated mask; no network or API credentials are needed. If necessary, build the mask first with `02b_build_california_mask.py`. For Spyder, open `07_pv_capacity_factor.py` after the extension dependencies are available. The CLI accepts an alternate `--project-dir` without changing source paths.

To reproduce the two tilt comparisons with distinct output names:

```bash
python scripts/07_pv_capacity_factor.py --tilt-deg 25 --tag 2020_01_tilt25 --headless
python scripts/07_pv_capacity_factor.py --tilt-deg 45 --tag 2020_01_tilt45 --headless
```

Outputs include per-interval CSVs, figures, model metadata with source checksums and assumptions, and individual summary CSVs. After the three runs, reproduce the committed tilt-comparison table with:

```python
import json
from pathlib import Path
import pandas as pd

rows = []
for tag in ["2020_01_tilt25", "2020_01", "2020_01_tilt45"]:
    metadata = json.loads(
        Path(f"results/tables/pv_model_metadata_{tag}.json").read_text()
    )
    summary = metadata["summary"]
    rows.append({
        "tag": tag,
        "tilt_deg": metadata["config"]["tilt_deg"],
        "mean_ac_cf": summary["mean_pv_ac_capacity_factor"],
        "max_ac_cf": summary["maximum_pv_ac_capacity_factor"],
        "intervals": summary["hourly_intervals"],
    })
pd.DataFrame(rows).to_csv(
    "results/tables/pv_tilt_sensitivity_2020_01.csv", index=False
)
```

No raw or generated NetCDF files are committed.

## Verification and limits

Ten automated tests passed, covering: dark-input zero output; rejection of missing inputs; horizontal-panel irradiance closure; temperature and loss responses; inverter clipping and rating normalization; NOCT reference conditions; preservation of low-sun interval irradiance; invalid parameter rejection; hourly alignment and temperature interpolation; and midpoint geometry. Gap, unit, and mask rejection are also covered within those checks. All three ERA5 scenario runs completed with finite, bounded output and no missing values. Their GHI reference agrees with the original saved proxy within float32 precision. These are implementation and consistency checks, not comparisons with observed PV production.

The model omits tracking, actual installation locations, terrain and row shading, spectral and explicit angle-of-incidence corrections, measured module-height wind, snow, and time-varying albedo or losses. It infers irradiance components from GHI and uses hour-average/midpoint approximations. The administrative mask and uniform deployment assumptions remain important limitations.

The separate [event comparison](event_comparison.md), implemented in `08_compare_event_definitions.py`, now uses this PV output for the hourly reference and a 48-hour combined-energy analysis. The original proxy-based event tables remain pilot results. Script 07 generates PV estimates; script 08 applies the separate event definitions.
