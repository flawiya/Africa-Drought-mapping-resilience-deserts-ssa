# 04 — 3SFCA Market Accessibility

Scripts to download OpenStreetMap agricultural support POIs and compute the Enhanced Three-Step Floating Catchment Area (3SFCA) spatial accessibility scores.

## Scripts

| Script | Description | Output |
|---|---|---|
| download_osm_pois.py | Downloads 48,890 agricultural support POIs across 21 SSA countries via Overpass API (3 categories) | outputs/data/pois_food_system_africa.gpkg |
| calculate_centroids.py | Computes geometric cropland centroids as routing origin points | Centroid GeoPackage |
| calculate_2sfca.py | Baseline 2SFCA model (Euclidean catchments) | District accessibility scores |
| compute_road_network_sfca.py | Enhanced 3SFCA using OSRM road network travel times (5 km walking + 50 km driving) | outputs/data/districts_2sfca_accessibility.gpkg |
| generate_sfca_stats.py | Summary statistics: tier distribution, Kruskal-Wallis tests, zero-access identification | Stats CSV + Markdown table |

## Infrastructure Categories
- **Agricultural Supply**: agrovets, seed/fertiliser suppliers, irrigation equipment
- **Financial Services**: microfinance institutions, mobile money agents, banks
- **Post-Harvest Logistics**: markets, storage facilities, mills, transport hubs

## Catchment Sizes
- 5 km (walking) -- used as primary analysis; identifies 39 zero-access districts
- 50 km (driving) -- sensitivity analysis; reduces zero-access count to 0
