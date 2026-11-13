# California boundary provenance

## Stored artifact

- File: `data/boundaries/california_census_2026.geojson`
- Source: U.S. Census Bureau TIGERweb, States layer, January 1, 2026 vintage.
- Selected feature: California, GEOID `06`.
- Format: GeoJSON FeatureCollection with one MultiPolygon feature.
- Requested output coordinate reference system: EPSG:4326 (longitude, latitude).
- Geometry: 7 polygon parts, no interior rings, 12,102 stored coordinate entries including ring closures.
- Size: 509,104 bytes.
- SHA-256: `459de647c6458ff9c1ce7b56148914cb7d5fb53f619a7e8aa2cfaf0ddd88661c`.

The repository contains the exact file supplied by the project author, unchanged. It preserves the geometry used for the January pilot rather than silently replacing it with a later download.

## Acquisition request

Service query endpoint:

https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer/0/query

Parameters:

```text
where=GEOID='06'
outFields=NAME,GEOID
returnGeometry=true
outSR=4326
f=geojson
```

The live service may change vintage or geometry. A future download is not guaranteed to have the same checksum; use the stored artifact to reproduce this pilot.

## Mask convention and verification

`scripts/02b_build_california_mask.py` selects ERA5 grid centers inside or on the administrative boundary using Shapely's `intersects_xy`.

On the documented 0.25-degree grid (latitude 42 to 32 degrees, longitude -125 to -114 degrees), the author's mask selects **695 of 1,845 centers**. An independent polygon-containment check on that grid reproduced the count during repository review. This check used the documented grid coordinates, not a newly opened ERA5 file.

The file was also checked for a single California feature, the expected GEOID, closed polygon rings, and valid longitude/latitude coordinate ranges.

This is a grid-center administrative mask, not fractional grid-cell coverage or a land-only mask. It includes state waters and does not encode wind-farm or photovoltaic deployment locations.

The subsequent [full-workflow verification](full_workflow_verification.md) rebuilt the mask with the actual supplied ERA5 coordinate grid using the unchanged Shapely script. Its 695 selected centers, coordinates, and values exactly matched the uploaded mask.
