"""
compute_road_network_sfca.py

Computes both 2SFCA and 3SFCA using the actual OSRM road network distance matrix.
Only computes for 50km (vehicle) threshold.
Saves outputs to the outputs directory.
"""

import pandas as pd
import numpy as np
import geopandas as gpd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent  # repo root
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "outputs"

DISTRICTS = DATA_DIR / "final_study_district.shp"
INPUT_CSV = DATA_DIR / "network_distance_matrix.csv"

BETA = 1.5  # Inverse-power distance decay parameter
D_MAX_M = 50_000.0

print("Loading road network distance matrix...")
df_dist_full = pd.read_csv(INPUT_CSV)
df_dist_full["ADM_NAME"] = df_dist_full["ADM_NAME"].str.strip().str.upper()
df_dist_full["COUNTRY"] = df_dist_full["COUNTRY"].str.strip().str.upper()

# Filter valid catchment (50km)
df_valid = df_dist_full[df_dist_full["network_dist_m"] <= D_MAX_M].copy()

# Count reachable facilities per district
facility_counts = df_valid.groupby(["ADM_NAME", "COUNTRY"]).size().reset_index(name="reachable_facilities_50km")

# Base distance decay G_ij
df_valid["dist_km_safe"] = np.maximum(df_valid["network_dist_m"] / 1000.0, 0.1)
df_valid["G_ij"] = df_valid["dist_km_safe"] ** (-BETA)

# Setup final GDF
print("Loading spatial districts...")
gdf_final = gpd.read_file(DISTRICTS)
gdf_final["ADM_NAME"] = gdf_final["ADM_NAME"].str.strip().str.upper()
gdf_final["COUNTRY"] = gdf_final["COUNTRY"].str.strip().str.upper()

# Merge facility counts
gdf_final = gdf_final.merge(facility_counts, on=["ADM_NAME", "COUNTRY"], how="left")
gdf_final["reachable_facilities_50km"] = gdf_final["reachable_facilities_50km"].fillna(0).astype(int)

print(f"\n--- Calculating for 50km threshold ---")

# 2SFCA Step 1: Demand D_j at each POI j
d2_demand = df_valid.groupby("poi_id")["G_ij"].sum().reset_index()
d2_demand.rename(columns={"G_ij": "D_j_2SFCA"}, inplace=True)
d2_demand["R_j_2SFCA"] = 1.0 / d2_demand["D_j_2SFCA"]

# 2SFCA Step 2: Sum ratios for District i
df_valid = df_valid.merge(d2_demand[["poi_id", "R_j_2SFCA"]], on="poi_id", how="left")
df_valid["A_2sfca_contrib"] = df_valid["R_j_2SFCA"] * df_valid["G_ij"]
A_2SFCA = df_valid.groupby(["ADM_NAME", "COUNTRY"])["A_2sfca_contrib"].sum().reset_index()
A_2SFCA.rename(columns={"A_2sfca_contrib": "A_2SFCA_50km"}, inplace=True)

if A_2SFCA["A_2SFCA_50km"].max() > 0:
    A_2SFCA["A_2SFCA_norm_50km"] = A_2SFCA["A_2SFCA_50km"] / A_2SFCA["A_2SFCA_50km"].max()
else:
    A_2SFCA["A_2SFCA_norm_50km"] = 0.0

# 3SFCA Step 1: Selection Weight W_ij
sum_G_i = df_valid.groupby(["ADM_NAME", "COUNTRY"])["G_ij"].sum().reset_index()
sum_G_i.rename(columns={"G_ij": "sum_G_i"}, inplace=True)
df_valid = df_valid.merge(sum_G_i, on=["ADM_NAME", "COUNTRY"], how="left")
df_valid["W_ij"] = df_valid["G_ij"] / df_valid["sum_G_i"]

# 3SFCA Step 2: Demand D_j at each POI j (assuming P_k = 1, so demand is just sum of W_kj)
df_valid["demand_kj_3sfca"] = df_valid["W_ij"]
d3_demand = df_valid.groupby("poi_id")["demand_kj_3sfca"].sum().reset_index()
d3_demand.rename(columns={"demand_kj_3sfca": "D_j_3SFCA"}, inplace=True)
d3_demand["R_j_3SFCA"] = 1.0 / d3_demand["D_j_3SFCA"]

# 3SFCA Step 3: Sum ratios for District i
df_valid = df_valid.merge(d3_demand[["poi_id", "R_j_3SFCA"]], on="poi_id", how="left")
df_valid["A_3sfca_contrib"] = df_valid["W_ij"] * df_valid["R_j_3SFCA"] * df_valid["G_ij"]
A_3SFCA = df_valid.groupby(["ADM_NAME", "COUNTRY"])["A_3sfca_contrib"].sum().reset_index()
A_3SFCA.rename(columns={"A_3sfca_contrib": "A_3SFCA_50km"}, inplace=True)

if A_3SFCA["A_3SFCA_50km"].max() > 0:
    A_3SFCA["A_3SFCA_norm_50km"] = A_3SFCA["A_3SFCA_50km"] / A_3SFCA["A_3SFCA_50km"].max()
else:
    A_3SFCA["A_3SFCA_norm_50km"] = 0.0

# Merge into final GDF
gdf_final = gdf_final.merge(A_2SFCA, on=["ADM_NAME", "COUNTRY"], how="left")
gdf_final["A_2SFCA_50km"] = gdf_final["A_2SFCA_50km"].fillna(0)
gdf_final["A_2SFCA_norm_50km"] = gdf_final["A_2SFCA_norm_50km"].fillna(0)

gdf_final = gdf_final.merge(A_3SFCA, on=["ADM_NAME", "COUNTRY"], how="left")
gdf_final["A_3SFCA_50km"] = gdf_final["A_3SFCA_50km"].fillna(0)
gdf_final["A_3SFCA_norm_50km"] = gdf_final["A_3SFCA_norm_50km"].fillna(0)

print(f"  2SFCA Stats: Max={gdf_final['A_2SFCA_50km'].max():.2f}, Zeros={(gdf_final['A_2SFCA_50km']==0).sum()}")
print(f"  3SFCA Stats: Max={gdf_final['A_3SFCA_50km'].max():.2f}, Zeros={(gdf_final['A_3SFCA_50km']==0).sum()}")

out_gpkg = OUTPUT_DIR / "districts_road_network_sfca_50km.gpkg"
gdf_final.to_file(out_gpkg, driver="GPKG")
print(f"\n[DONE] Saved 50km road network SFCA accessibility scores to {out_gpkg}")
