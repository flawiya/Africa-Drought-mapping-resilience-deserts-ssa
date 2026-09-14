import os
import sys
import pandas as pd
import geopandas as gpd
import numpy as np
from shapely.geometry import Point
from pathlib import Path

# Setup paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent  # repo root
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "outputs"

# Inputs
SHP_FILE = DATA_DIR / "final_study_district.shp"
DISTRICTS_LIST_CSV = DATA_DIR / "refined_361_districts_list.csv"
CLASSIFIED_POIS_CSV = OUTPUT_DIR / "africa_354_classified_pois.csv"

# Outputs
OUTPUT_GEOJSON = OUTPUT_DIR / "refined_354_districts_with_accessibility.geojson"
OUTPUT_CSV = OUTPUT_DIR / "refined_354_districts_with_accessibility.csv"

def run_2sfca(gdf_districts, gdf_pois, d0, demand_col="Calc_Cropland_km2"):
    """
    Computes 2SFCA accessibility scores on projected geometries (in meters).
    gdf_districts: GeoDataFrame of districts projected in ESRI:102022
    gdf_pois: GeoDataFrame of supply POIs projected in ESRI:102022
    d0: Catchment radius in meters
    """
    gdf_pois = gdf_pois.copy()
    gdf_pois["capacity"] = 1.0  # Assumes each POI has a capacity of 1 (equal weight)
    
    # Step 1: Calculate Provider-to-Population Ratio (R_j) for each supply point
    r_j_scores = []
    
    # Pre-calculate centroids to speed up distance checks
    district_centroids = gdf_districts["centroid"]
    
    for idx, poi in gdf_pois.iterrows():
        poi_geom = poi.geometry
        # Compute Euclidean distance in projected coordinates
        dists = district_centroids.distance(poi_geom)
        # Find districts within the threshold distance d0
        within_catchment = gdf_districts[dists <= d0]
        
        sum_demand = within_catchment[demand_col].sum()
        if sum_demand > 0:
            r_j = poi["capacity"] / sum_demand
        else:
            r_j = 0.0
        
        r_j_scores.append(r_j)
        
    gdf_pois["R_j"] = r_j_scores
    
    # Step 2: Calculate Accessibility Score (A_i) for each district
    a_i_scores = []
    poi_geoms = gdf_pois.geometry
    
    for idx, dist in gdf_districts.iterrows():
        centroid = dist["centroid"]
        # Compute distances from centroid to all POIs
        dists = poi_geoms.distance(centroid)
        # Find POIs within the threshold distance d0
        within_catchment = gdf_pois[dists <= d0]
        
        a_i = within_catchment["R_j"].sum()
        a_i_scores.append(a_i)
        
    return a_i_scores

def main():
    print("--- STARTING 2SFCA ACCESSIBILITY CALCULATOR ---")
    
    # Verify input files
    for path, name in [(DISTRICTS_LIST_CSV, "Districts List"), 
                       (SHP_FILE, "Study Districts Shapefile"), 
                       (CLASSIFIED_POIS_CSV, "Classified POIs CSV")]:
        if not path.exists():
            print(f"[ERROR] Missing required file: {name} at {path}")
            sys.exit(1)
            
    # 1. Load datasets
    df_list = pd.read_csv(DISTRICTS_LIST_CSV)
    gdf_districts = gpd.read_file(SHP_FILE)
    df_pois = pd.read_csv(CLASSIFIED_POIS_CSV)
    
    # Standardize join key
    gdf_districts["join_key"] = gdf_districts["join_key"].astype(str).str.strip().str.upper()
    df_list["join_key"] = df_list["join_key"].astype(str).str.strip().str.upper()
    
    # Clean list columns to avoid merge clashes
    df_list_clean = df_list[["join_key", "Calc_Cropland_km2", "Calc_Total_km2"]].copy()
    
    # Merge geometries with cropland demand metadata directly
    gdf_districts = gdf_districts.merge(df_list_clean, on="join_key", how="inner")
    print(f"Loaded {len(gdf_districts)} active districts with geometry and cropland metadata.")
    
    # Project to Africa Albers Equal Area Conic (ESRI:102022)
    print("Projecting districts and POIs to ESRI:102022...")
    gdf_districts_proj = gdf_districts.to_crs("ESRI:102022")
    
    # Pre-calculate centroids in projected CRS
    gdf_districts_proj["centroid"] = gdf_districts_proj.geometry.centroid
    
    # Create GeoDataFrame for POIs and project it
    geometry = [Point(xy) for xy in zip(df_pois["lon"], df_pois["lat"])]
    gdf_pois = gpd.GeoDataFrame(df_pois, geometry=geometry, crs="EPSG:4326")
    gdf_pois_proj = gdf_pois.to_crs("ESRI:102022")
    
    # 2. Run 2SFCA for each class and threshold
    poi_classes = [
        "Agricultural Input (Drought Mitigation)",
        "Agricultural Output (Market Access)",
        "Post-Harvest & Processing (Logistics)",
        "Financial Accessibility"
    ]
    
    # Define thresholds in meters
    d0_walking = 15000     # 15 km (~3 hours walking)
    d0_motorized = 50000   # 50 km (~1 hour driving)
    
    for cls in poi_classes:
        cls_short = cls.split(" (")[0].replace(" & ", "_").replace(" ", "_").lower()
        print(f"\nProcessing POI Class: {cls}")
        
        # Filter POIs for this class
        gdf_cls_pois = gdf_pois_proj[gdf_pois_proj["poi_class"] == cls]
        print(f"  Found {len(gdf_cls_pois)} POIs in this class.")
        
        if len(gdf_cls_pois) == 0:
            print("  [WARNING] No POIs found. Setting accessibility scores to 0.0.")
            gdf_districts_proj[f"access_{cls_short}_15km"] = 0.0
            gdf_districts_proj[f"access_{cls_short}_50km"] = 0.0
            continue
            
        # Run 2SFCA
        print("  Running 2SFCA (15 km catchment)...")
        gdf_districts_proj[f"access_{cls_short}_15km"] = run_2sfca(gdf_districts_proj, gdf_cls_pois, d0_walking)
        
        print("  Running 2SFCA (50 km catchment)...")
        gdf_districts_proj[f"access_{cls_short}_50km"] = run_2sfca(gdf_districts_proj, gdf_cls_pois, d0_motorized)
        
        # Summary statistics
        mean_15 = gdf_districts_proj[f"access_{cls_short}_15km"].mean()
        mean_50 = gdf_districts_proj[f"access_{cls_short}_50km"].mean()
        print(f"  15km Mean Score: {mean_15:.6f} | 50km Mean Score: {mean_50:.6f}")
        
    # Save projected GeoJSON
    gdf_districts_proj_save = gdf_districts_proj.drop(columns=["centroid"])
    gdf_districts_proj_save.to_file(OUTPUT_GEOJSON, driver="GeoJSON")
    print(f"\n[SUCCESS] Saved GeoJSON with accessibility scores to {OUTPUT_GEOJSON}")
    
    # Save CSV (excluding geometries to keep it lightweight)
    df_output = pd.DataFrame(gdf_districts_proj.drop(columns=["geometry", "centroid"]))
    df_output.to_csv(OUTPUT_CSV, index=False)
    print(f"[SUCCESS] Saved CSV with accessibility scores to {OUTPUT_CSV}")

if __name__ == "__main__":
    main()
