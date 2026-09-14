# 03 — GLAD 30m Cropland Masking

Scripts to process the GLAD 30m Global Cropland Map (2019) and derive crop-type specific district-level statistics.

## Scripts

| Script | Description | Output |
|---|---|---|
| glad_cropland_mask.py | Extracts GLAD 30m cropland pixels per GAUL district, computes cropland area and pixel counts | GLAD-GAUL joined GeoPackage |
| dmin_glad_csv.py | Exports GLAD district-level crop statistics to CSV for merging with drought data | data/final-GLAD-50-2019.csv |
| overlapping_pixel_solver.py | Area-weighted pixel allocation engine: resolves boundary-crossing 30m pixels across district polygons | Corrected pixel-district allocation |

## Methodology Note
Geometric cropland centroids (not population-weighted) are used as OSRM origin demand points in 04_sfca_accessibility to avoid urban settlement bias in routing.
