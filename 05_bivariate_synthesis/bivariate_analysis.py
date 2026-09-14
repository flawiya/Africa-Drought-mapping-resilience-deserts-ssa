import os
import sys
import pandas as pd
import geopandas as gpd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path

# Setup paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent  # repo root
OUTPUT_DIR = PROJECT_ROOT / "outputs"

DATA_DIR = PROJECT_ROOT / "data"

# Inputs
_geojson = OUTPUT_DIR / "refined_354_districts_with_accessibility.geojson"
if not _geojson.exists():
    _geojson = DATA_DIR / "refined_354_districts_with_accessibility.geojson"
ACCESSIBILITY_GEOJSON = _geojson

# Outputs
BIVARIATE_CSV = OUTPUT_DIR / "bivariate_food_insecurity_analysis.csv"
BIVARIATE_SUMMARY_TXT = OUTPUT_DIR / "bivariate_analysis_summary.txt"
BIVARIATE_MAP_PNG = OUTPUT_DIR / "bivariate_food_insecurity_map.png"
BIVARIATE_MAP_HTML = OUTPUT_DIR / "bivariate_food_insecurity_interactive.html"

def main():
    print("--- STARTING BIVARIATE ANALYSIS & MAPPING ---")
    
    if not ACCESSIBILITY_GEOJSON.exists():
        print(f"[ERROR] Accessibility GeoJSON not found: {ACCESSIBILITY_GEOJSON}")
        sys.exit(1)
        
    # 1. Load GeoDataFrame
    gdf = gpd.read_file(ACCESSIBILITY_GEOJSON)
    print(f"Loaded {len(gdf)} districts with accessibility scores.")
    
    # 2. Define Drought Risk from Hierarchical Clusters (hc_k3)
    # hc_k3 has:
    # 0 = Moderate Vulnerability (Cluster 1)
    # 1 = High Vulnerability (Cluster 2 - Eastern Belt / Tanzania/Zambia/Burundi)
    # 2 = High Vulnerability (Cluster 3 - Southern Belt / Malawi/Mozambique/Swaziland)
    
    # Let's map hc_k3 values to labels
    def map_drought_risk(row):
        c = row["hc_k3"]
        if c == 0:
            return "Low/Medium Risk (Cluster 1)"
        elif c == 1:
            return "High Risk (Cluster 2 - Eastern Belt)"
        elif c == 2:
            return "High Risk (Cluster 3 - Southern Belt)"
        else:
            return "Unknown"
            
    gdf["drought_risk_label"] = gdf.apply(map_drought_risk, axis=1)
    
    # 3. Classify Accessibility into Terciles
    # We will use 'access_agricultural_market_access_50km' as our output (Market Access) accessibility score
    # and 'access_agricultural_input_50km' as input accessibility score
    # Let's use the sum of market access and input access as a General Agricultural Service Access Score
    access_col_market = "access_agricultural_output_50km"
    access_col_input = "access_agricultural_input_50km"
    
    # Let's check if the columns exist (we standardized column names in calculate_2sfca.py)
    # Columns in calculate_2sfca.py: access_agricultural_input_50km, access_agricultural_output_50km
    
    gdf["total_access_score"] = gdf[access_col_market] + gdf[access_col_input]
    
    # Calculate tercile thresholds
    q33 = gdf["total_access_score"].quantile(0.33)
    q67 = gdf["total_access_score"].quantile(0.67)
    print(f"Accessibility Tercile Thresholds: 33% = {q33:.6f}, 67% = {q67:.6f}")
    
    def map_access_class(val):
        if val <= q33:
            return "Low Access"
        elif val <= q67:
            return "Medium Access"
        else:
            return "High Access"
            
    gdf["access_class"] = gdf["total_access_score"].apply(map_access_class)
    
    # 4. Generate Bivariate Matrix (3x3 grid)
    # X-axis: Drought Risk (Cluster 1, 2, 3)
    # Y-axis: Accessibility (High, Medium, Low)
    bivariate_summary = []
    bivariate_summary.append("Bivariate Food Insecurity Risk Matrix (Districts Count)")
    bivariate_summary.append("==========================================================")
    
    matrix = pd.crosstab(gdf["access_class"], gdf["drought_risk_label"])
    bivariate_summary.append(matrix.to_string())
    bivariate_summary.append("\n" + "=" * 58 + "\n")
    
    # Identify Hotspots (High Risk + Low Access)
    # These are districts in Cluster 2 or 3 with "Low Access"
    # hc_k3 has codes: 0 (Cluster 1), 1 (Cluster 2), 2 (Cluster 3)
    hotspots = gdf[(gdf["hc_k3"].isin([1, 2])) & (gdf["access_class"] == "Low Access")].copy()
    bivariate_summary.append(f"TOTAL HOTSPOTS IDENTIFIED (High Risk & Low Access): {len(hotspots)}")
    bivariate_summary.append("-" * 58)
    
    # Print top country distribution of hotspots
    hotspot_countries = hotspots["COUNTRY"].value_counts()
    bivariate_summary.append("Hotspots by Country:")
    for country, count in hotspot_countries.items():
        bivariate_summary.append(f"  - {country}: {count} districts")
        
    bivariate_summary.append("\nTop 15 Most Vulnerable Districts (Hotspots):")
    hotspots_sorted = hotspots.sort_values(by="total_access_score", ascending=True)
    for idx, row in hotspots_sorted.head(15).iterrows():
        bivariate_summary.append(f"  - {row['COUNTRY']} - {row['ADM_NAME']}: Cluster {int(row['hc_k3']) + 1} | Access Score: {row['total_access_score']:.6f}")
        
    # Write summary text
    summary_text = "\n".join(bivariate_summary)
    print(summary_text)
    with open(BIVARIATE_SUMMARY_TXT, "w") as f:
        f.write(summary_text)
        
    # Save the classification data
    df_save = pd.DataFrame(gdf.drop(columns=["geometry"]))
    df_save.to_csv(BIVARIATE_CSV, index=False)
    print(f"Saved bivariate data to {BIVARIATE_CSV}")
    
    # 5. Plot Bivariate Map
    print("\nGenerating Bivariate Map...")
    fig, ax = plt.subplots(figsize=(12, 12))
    
    # Define a 3x3 color scale
    # Y-axis (Access): High, Medium, Low
    # X-axis (Risk): Cluster 1 (Low), Cluster 2 (Medium), Cluster 3 (High)
    # We will assign color codes to each combination:
    bivariate_colors = {
        # Cluster 1 (Low/Med Risk)
        ("Low/Medium Risk (Cluster 1)", "High Access"): "#85c0f9",   # Soft Blue (Resilient)
        ("Low/Medium Risk (Cluster 1)", "Medium Access"): "#a6b5e2", # Grey-Blue
        ("Low/Medium Risk (Cluster 1)", "Low Access"): "#c2aabf",    # Light Purple
        
        # Cluster 2 (High Risk - Eastern)
        ("High Risk (Cluster 2 - Eastern Belt)", "High Access"): "#f9e085",   # Yellow-Green (Resilient agricultural area)
        ("High Risk (Cluster 2 - Eastern Belt)", "Medium Access"): "#e0a685", # Orange
        ("High Risk (Cluster 2 - Eastern Belt)", "Low Access"): "#e65555",    # Soft Red (Vulnerable)
        
        # Cluster 3 (High Risk - Southern)
        ("High Risk (Cluster 3 - Southern Belt)", "High Access"): "#f5af85",   # Orange-Red
        ("High Risk (Cluster 3 - Southern Belt)", "Medium Access"): "#b85555", # Dark Red
        ("High Risk (Cluster 3 - Southern Belt)", "Low Access"): "#800000",    # Maroon (CRITICAL HOTSPOT)
    }
    
    def get_color(row):
        key = (row["drought_risk_label"], row["access_class"])
        return bivariate_colors.get(key, "#cfd8dc")
        
    gdf["map_color"] = gdf.apply(get_color, axis=1)
    
    # Plot base map of Africa (just standard outline or all districts)
    # Project to Albers for equal area plotting
    gdf_proj = gdf.to_crs("ESRI:102022")
    
    # Draw districts colored by their bivariate class
    for (risk_lbl, access_lbl), color in bivariate_colors.items():
        subset = gdf_proj[(gdf_proj["drought_risk_label"] == risk_lbl) & (gdf_proj["access_class"] == access_lbl)]
        if not subset.empty:
            subset.plot(ax=ax, color=color, edgecolor="black", linewidth=0.2)
            
    # Format map
    ax.set_title("Bivariate Food Insecurity Map: Drought Vulnerability vs. Agricultural Service Access\n(Refined 354 Districts in Africa)", 
                 fontsize=14, fontweight="bold", pad=15)
    
    # Legend
    legend_patches = []
    for (risk_lbl, access_lbl), color in bivariate_colors.items():
        # Shorten label for cleaner legend
        short_lbl = f"{risk_lbl.split(' (')[0]} / {access_lbl}"
        legend_patches.append(mpatches.Patch(color=color, label=short_lbl))
        
    ax.legend(handles=legend_patches, loc="lower left", fontsize=8, frameon=True, facecolor="white", ncol=2)
    ax.set_axis_off()
    
    plt.tight_layout()
    plt.savefig(BIVARIATE_MAP_PNG, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Saved Bivariate Map to {BIVARIATE_MAP_PNG}")
    
    # 6. Generate Folium Interactive Map
    print("Generating Interactive Bivariate Map (HTML)...")
    # Simplify geometry for fast loading
    gdf_wgs84 = gdf.to_crs(epsg=4326)
    gdf_wgs84["geometry"] = gdf_wgs84["geometry"].simplify(tolerance=0.01, preserve_topology=True)
    
    m = gdf_wgs84.explore(
        column="total_access_score",
        cmap="YlOrRd",
        legend=True,
        tooltip=["COUNTRY", "ADM_NAME", "hc_k3", "access_class", "total_access_score"],
        popup=True,
        tiles="CartoDB positron"
    )
    m.save(BIVARIATE_MAP_HTML)
    print(f"Saved Interactive Map to {BIVARIATE_MAP_HTML}")
    
    print("\n[SUCCESS] BIVARIATE ANALYSIS COMPLETED.")

if __name__ == "__main__":
    main()
