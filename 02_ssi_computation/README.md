# 02 — SSI Computation & Drought Risk Index

Scripts to compute the Standardised Soil Moisture Index (SSI), aggregate drought history, and derive the Drought Risk Index (DRI).

## Scripts

| Script | Description | Output |
|---|---|---|
| ssi_lib.py | Core SSI library: percentile normalisation, threshold classification, drought-day counting | (library — import by other scripts) |
| process_drought_history.py | Main pipeline: computes multi-threshold SSI drought days per district per year (2000-2025) across 21 SSA countries | outputs/data/Africa_Maize_Drought_Annual_MultiThreshold.csv |
| merge_drought_to_gadm.py | Joins drought output to GAUL/GADM district metadata (country, name, geometry) | outputs/data/drought_annual_with_gadm_metadata.csv |
| compute_enso_correlation.py | Correlates annual drought day counts with ENSO indices (Nino3.4 ONI) to identify teleconnection spikes | Correlation table + figure |

## Methodology Note
SSI is computed against a 25-year (2000-2025) Julian Day baseline using non-parametric percentile ranks, capturing flash droughts that monthly indices miss.
Drought thresholds: SSI <= -1.0 (moderate), SSI <= -1.5 (severe), SSI <= -2.0 (extreme).
