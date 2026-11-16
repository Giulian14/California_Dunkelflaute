# Event definition review

Status: this design has now been implemented as a separately labeled January scenario comparison, reviewed November 16, 2026. See [implementation, results, and limits](event_comparison.md). Original pilot results are preserved; this is not a finalized multi-year climatological definition.

## Reference: simultaneous low generation

Retain the pilot's strict hourly condition: wind CF < 0.20 AND solar CF < 0.20. For the reference prolonged-event catalogue, require at least 24 consecutive complete hourly intervals; also report minimum-duration sensitivity.

Li et al. (2021) use simultaneous hourly 20% thresholds and explicitly include calm nighttime conditions. Our 24-hour minimum is a project duration criterion; their paper also examines longer events.

Source: [Li et al., A Brief Climatology of Dunkelflaute Events](https://doi.org/10.3390/en14206508).

The original pilot uses a solar irradiance proxy rather than modeled PV CF. Its preliminary results are preserved, and a separate comparison now uses the documented PV model. Zero qualifying 24-hour periods in January is a valid result, not a reason to change thresholds to obtain events. The truncated initial period has unknown full duration.

## Complementary comparison: low combined energy over 48 hours

Mockert et al. (2023), Sections 2.3–2.4, combine technology CFs using installed-capacity weights, then identify low 48-hour running means. Their 0.06 threshold is specific to their German study; it is not established for California. They include all hours contributing to qualifying windows.

Source: [Mockert et al., Meteorological conditions during periods of low wind speed and insolation in Germany](https://doi.org/10.1002/met.2141).

For our two-technology comparison:

`combined_CF = a * wind_CF + (1 - a) * PV_CF`

Here a is wind's share of rated wind-plus-PV capacity, not its annual generation share. The tested initial scenario is a = 0.50, with 0.25 and 0.75 as sensitivity scenarios. These hypothetical mixes do not describe California's actual fleet.

The January comparison tests 0.06, with 0.05 and 0.10 sensitivity thresholds, using the new PV model and the illustrative wind model. Do not calibrate it merely to obtain a desired event count.

A qualifying 48-hour average can contain higher-generation individual hours. It is therefore a different question from requiring every hour to be low. Use complete windows, merge overlapping or directly adjacent qualifying window intervals, and flag catalogue boundaries. Count event duration from the union of covered hours, not from the number of qualifying window endpoints.

## Interpretation and remaining scientific work

A 48-hour average spans two day–night cycles but does not by itself establish climatological rarity. Assess seasonal baselines with the multi-year data when making claims about unusual conditions.

Keep the reference and comparison catalogues distinct. Combined low generation can occur without each technology independently being low.

A documented PV model and the two event methods have now been implemented. Model validation, geographic weighting, capacity-mix assumptions, multi-year climatology, and temperature extremes remain separate scientific tasks. Neither event definition alone measures electricity shortages.
