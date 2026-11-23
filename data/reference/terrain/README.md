# Terrain reference provenance

The source manifest records public WeatherBench 2 ERA5 static-field chunks and USGS EPQS point requests, retrieved November 23, 2026. Original binary chunks and raw DEM responses remain outside Git; `16a_fetch_terrain_references.py` can replay the manifest with byte checks or verify an offline cache. Static field metadata and the source's license are retained here. The derived plant table is in `results/tables/wind_terrain_site_audit_2020_01.csv`.

Contains modified Copernicus Climate Change Service information (2026). Neither the European Commission nor ECMWF is responsible for any use of the Copernicus information or data. WeatherBench 2 supplies the public ERA5 archive; USGS 3DEP/EPQS supplies interpolated point DEM elevations.

Point elevations and grid-scale geopotential heights have different support and vertical definitions. They are not turbine surveys or a basis for automatic wind correction. See [method and limits](../../../docs/wind_terrain_and_curve_audit.md).
