---
name: geospatial-analysis
description: Perform GIS joins, raster zonal statistics, spatial grids, spatial autocorrelation and maps.
---

# geospatial-analysis

Use GeoPandas, Rasterio, PySAL. Audit source CRS; use EPSG:26918 meter coordinates for grid/distance/area, EPSG:4326 for web maps. Check boundaries, raster nodata and vertical units. Use area-weighted fractions. Report join loss and coverage. For Moran I/LISA use suitable weights and permutations, report multiple-testing correction. Use spatial blocks for holdouts. Catch basin density is a proxy; non-MS4 is unknown unless verified.

Read `CLAUDE.md` and `docs/research_plan.md` before acting. Follow `docs/implementation.md` and save artifacts under the configured run directory.
