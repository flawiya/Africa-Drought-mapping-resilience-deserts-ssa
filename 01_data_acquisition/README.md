# 01 — Data Acquisition

Scripts to download and export all raw climate and geospatial data used in this study via Google Earth Engine (GEE) and public APIs.

## Prerequisites
- A valid GEE account with an active project
- Set GEE_PROJECT_ID in your .env file (see root .env.example)
- Run earthengine authenticate once before executing these scripts

## Scripts

| Script | Description | Output |
|---|---|---|
| `acquire_era5_land.py` | Downloads ERA5-Land daily soil moisture (Layer 2, 7-28cm), temperature, PEV (2000-2025) via GEE | CSV timeseries per district |
| `acquire_chirps_rainfall.py` | Downloads CHIRPS daily rainfall across SSA agricultural districts | CSV timeseries |
| `acquire_modis_ndvi.py` | Downloads MODIS MOD13A2 NDVI (500m, 16-day) | CSV timeseries |
| `acquire_modis_lst.py` | Downloads MODIS MOD11A2 Land Surface Temperature | CSV timeseries |
| `acquire_csic_spei.py` | Downloads CSIC SPEI-3 (3-month Standardised Precipitation-Evapotranspiration Index) | CSV timeseries |

## Notes
- GEE exports are asynchronous -- monitor progress at https://code.earthengine.google.com/ under the Tasks tab
- Output files are large (>1 GB for ERA5 full SSA) and are NOT committed to this repository -- see root README for download instructions
