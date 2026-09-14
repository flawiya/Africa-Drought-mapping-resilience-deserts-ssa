# 05 — Bivariate Synthesis (Resilience Deserts)

Scripts to perform spatially-constrained hierarchical clustering and produce the bivariate Drought Risk x Market Isolation classification.

## Scripts

| Script | Description | Output |
|---|---|---|
| `main_analysis_pipeline.py` | Main analysis pipeline: loads all processed data, computes DRI, normalises scores, runs sensitivity analyses | Consolidated district dataset |
| `spatial_clustering.py` | Spatially-constrained hierarchical clustering (Ward linkage + spatial contiguity matrix, K=3) | Cluster assignments CSV |
| `bivariate_analysis.py` | Bivariate 3x3 matrix classification (DRI* x I*); identifies Resilience Desert districts | Bivariate classification GeoPackage |

## Resilience Desert Definition
A district is classified as a Resilience Desert if:
  - Normalised DRI* >= 0.67  (upper tertile of drought exposure), AND
  - Normalised Isolation I* >= 0.67  (upper tertile of market isolation, where I* = 1 - A*)

Both conditions must hold simultaneously. 118 districts (33.2%) meet this threshold under the 5 km walking catchment.
