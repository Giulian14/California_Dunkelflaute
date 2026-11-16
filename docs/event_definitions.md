# Event definition review

Status: proposed analysis design, reviewed November 16, 2026. No pilot code, thresholds, or saved results are changed by this note.

## Reference: simultaneous low generation

Retain the pilot's strict hourly condition: wind CF < 0.20 AND solar CF < 0.20. For the reference prolonged-event catalogue, require at least 24 consecutive complete hourly intervals; also report minimum-duration sensitivity.

Li et al. (2021) use simultaneous hourly 20% thresholds and explicitly include calm nighttime conditions. Our 24-hour minimum is a project duration criterion; their paper also examines longer events.

Source: [Li et al., A Brief Climatology of Dunkelflaute Events](https://doi.org/10.3390/en14206508).

The pilot still uses a solar irradiance proxy rather than modeled PV CF. Preserve its results as preliminary. Zero qualifying 24-hour periods in January is a valid result, not a reason to change thresholds to obtain events. The truncated initial period has unknown full duration.

## Complementary comparison: low combined energy over 48 hours

Mockert et al. (2023), Sections 2.3–2.4, combine technology CFs using installed-capacity weights, then identify low 48-hour running means. Their 0.06 threshold is specific to their German study; it is not established for California. They include all hours contributing to qualifying windows.

Source: [Mockert et al., Meteorological conditions during periods of low wind speed and insolation in Germany](https://doi.org/10.1002/met.2141).

For our two-technology comparison:

`combined_CF = a * wind_CF + (1 - a) * PV_CF`

Here a is wind's share of rated wind-plus-PV capacity, not its annual generation share. A proposed initial scenario is a = 0.50, with 0.25 and 0.75 as sensitivity scenarios. These hypothetical mixes do not describe California's actual fleet.

Test 0.06 as a literature comparison, with threshold sensitivity, after upgrading the generation models. Do not calibrate it merely to obtain a desired event count.

A qualifying 48-hour average can contain higher-generation individual hours. It is therefore a different question from requiring every hour to be low. Use complete windows, merge overlapping or directly adjacent qualifying window intervals, and flag catalogue boundaries. Count event duration from the union of covered hours, not from the number of qualifying window endpoints.

## Interpretation and next implementation step

A 48-hour average spans two day–night cycles but does not by itself establish climatological rarity. Assess seasonal baselines with the multi-year data when making claims about unusual conditions.

Keep the reference and comparison catalogues distinct. Combined low generation can occur without each technology independently being low.

Next, implement a documented PV generation model before applying CF-based comparisons. Model choice, geographic weighting, capacity-mix assumptions, and temperature extremes remain separate analysis decisions. Neither event definition alone measures electricity shortages.
