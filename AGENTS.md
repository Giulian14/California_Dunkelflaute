# Project working instructions

- Maintain `docs/research_log.md` for each scientific or implementation change. Record the session date, purpose, inputs and versions, assumptions, code and outputs, checks, quantitative results, and remaining limitations. Link to run metadata and verification records.
- Distinguish dated execution records from retrospectively reconstructed history. Do not invent earlier execution dates, steps, or successful checks.
- Preserve original pilot artifacts. Add named scenarios and explain changes in physical definitions, denominators, temporal support, or spatial weighting.
- Keep source references and file checksums for derived scientific results. Retain third-party notices for redistributed reference data.
- Keep raw ERA5 NetCDF files, downloaded archives, and credentials outside Git. Reuse existing inputs rather than repeating their downloads.
- Distinguish computational reproduction and sensitivity analysis from validation against observed generation. Do not label hypothetical layouts or portfolios as the actual historical fleet.
- Keep `README.md`, method notes, and the research log consistent with the code. Report boundary uncertainty and incomplete rolling-window context.
- Add meaningful tests for changes to scientific calculations, units, time alignment, or event extraction. Do not alter thresholds just to obtain a desired number of events.
