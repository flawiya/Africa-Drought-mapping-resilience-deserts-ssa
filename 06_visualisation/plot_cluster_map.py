import os
import sys
import pandas as pd
import geopandas as gpd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent  # repo root
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

_shp = DATA_DIR / "final_study_district.shp"
if not _shp.exists():
    _shp = OUTPUT_DIR / "final_study_district.shp"
SHP_FILE = _shp

MAP_PNG = OUTPUT_DIR / "refined_361_hierarchical_k3_map.png"
MAP_HTML = OUTPUT_DIR / "refined_361_hierarchical_k3_map.html"

def main():
    print("--- GENERATING STABLE HIERARCHICAL K=3 CLUSTER MAPS ---")
    
    if not SHP_FILE.exists():
        print(f"[ERROR] Final shapefile not found at {SHP_FILE}")
        sys.exit(1)
        
    print(f"Loading shapefile: {SHP_FILE}")
    gdf = gpd.read_file(SHP_FILE)
    print(f"Loaded {len(gdf)} districts.")
    
    # Check if hc_k3 column is present
    if "hc_k3" not in gdf.columns:
        print("[ERROR] Column 'hc_k3' (hierarchical_k3) is missing from the shapefile.")
        sys.exit(1)
        
    print("Cluster value counts:")
    print(gdf["hc_k3"].value_counts())
    
    # Map raw numeric cluster codes (0, 1, 2) to descriptive labels
    # 0 -> Cluster 1: Moderate Vulnerability (151 districts)
    # 1 -> Cluster 2: High Vulnerability (85 districts)
    # 2 -> Cluster 3: High Vulnerability (118 districts)
    def map_cluster_label(val):
        if val == 0:
            return "Cluster 1: Moderate Vulnerability (n=151)"
        elif val == 1:
            return "Cluster 2: High Vulnerability - Tanzania/Zambia/Burundi (n=85)"
        elif val == 2:
            return "Cluster 3: High Vulnerability - Malawi/Mozambique/Swaziland (n=118)"
        else:
            return f"Cluster Unknown ({val})"
            
    gdf["cluster_label"] = gdf["hc_k3"].apply(map_cluster_label)
    
    # Define colors
    colors = {
        0: "#27ae60",  # Green (Moderate Vulnerability)
        1: "#f39c12",  # Orange (High Vulnerability - Tanzania/Zambia/Burundi)
        2: "#c0392b"   # Red (High Vulnerability - Malawi/Mozambique/Swaziland)
    }
    
    # 1. Plot Static Map (Projected CRS)
    print("Plotting static PNG map...")
    # Project to Africa equal area for clean geographic rendering
    gdf_proj = gdf.to_crs("ESRI:102022")
    
    fig, ax = plt.subplots(figsize=(10, 10))
    
    for cluster_id, color in colors.items():
        subset = gdf_proj[gdf_proj["hc_k3"] == cluster_id]
        if not subset.empty:
            subset.plot(ax=ax, color=color, edgecolor="black", linewidth=0.2)
            
    ax.set_title("Stable Hierarchical Clustering (K = 3) of Drought Trajectories\n(Refined 354 Districts in Africa)", 
                 fontsize=12, fontweight="bold", pad=15)
                 
    # Create legend
    legend_patches = [
        mpatches.Patch(color=colors[0], label="Cluster 1: Moderate (Kenya, Uganda, Egypt)"),
        mpatches.Patch(color=colors[1], label="Cluster 2: High (Tanzania, Zambia, Burundi)"),
        mpatches.Patch(color=colors[2], label="Cluster 3: High (Malawi, Mozambique, Swaziland)")
    ]
    ax.legend(handles=legend_patches, loc="lower left", fontsize=9, frameon=True, facecolor="white")
    ax.set_axis_off()
    plt.tight_layout()
    plt.savefig(MAP_PNG, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Saved static map to {MAP_PNG}")
    
    # 2. Plot Interactive Folium HTML Map
    print("Plotting interactive HTML map...")
    gdf_wgs84 = gdf.to_crs(epsg=4326)
    # Simplify geometry for fast loading in browser
    gdf_wgs84["geometry"] = gdf_wgs84["geometry"].simplify(tolerance=0.01, preserve_topology=True)
    
    from matplotlib.colors import ListedColormap
    custom_cmap = ListedColormap(["#27ae60", "#f39c12", "#c0392b"])
    
    # Create interactive explore map
    m = gdf_wgs84.explore(
        column="cluster_label",
        cmap=custom_cmap,  # Order matches alphabetical sorted unique values
        legend=True,
        tooltip=["COUNTRY", "ADM_NAME", "cluster_label", "maize_pct"],
        popup=True,
        tiles="CartoDB positron"
    )
    
    m.save(MAP_HTML)
    print(f"Saved interactive map to {MAP_HTML}")
    print("[SUCCESS] Maps generated.")

if __name__ == "__main__":
    main()
