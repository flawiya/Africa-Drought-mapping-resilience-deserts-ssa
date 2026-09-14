import geopandas as gpd
import shutil
from pathlib import Path

# Setup paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent  # repo root
OUTPUT_DIR = PROJECT_ROOT / "outputs"
DATA_DIR = PROJECT_ROOT / "data"

SHP_PATH = DATA_DIR / "final_study_district.shp"

def main():
    print("--- STARTING CENTROID CALCULATION ---")
    if not SHP_PATH.exists():
        print(f"[ERROR] Shapefile not found at {SHP_PATH}")
        return
        
    print(f"Loading shapefile from {SHP_PATH}...")
    gdf = gpd.read_file(SHP_PATH)
    print(f"Loaded {len(gdf)} districts.")
    
    # Ensure CRS is projected or compute in EPSG:4326 directly
    # To get accurate geographic centroids for polygons, computing directly on WGS84 or projecting first is standard.
    # GeoPandas recommends projecting to an equal-area projection like ESRI:102022 to calculate centroids in meters,
    # and then reprojecting back to EPSG:4326 to get accurate latitude and longitude.
    print("Projecting to equal-area CRS (ESRI:102022) for accurate centroid calculation...")
    gdf_proj = gdf.to_crs("ESRI:102022")
    centroids_proj = gdf_proj.geometry.centroid
    
    print("Reprojecting centroids back to EPSG:4326 to get geographic coordinates...")
    centroids_wgs84 = centroids_proj.to_crs(epsg=4326)
    
    gdf["cent_lon"] = centroids_wgs84.geometry.x
    gdf["cent_lat"] = centroids_wgs84.geometry.y
    
    print("\nSample calculated centroids:")
    print(gdf[["COUNTRY", "ADM_NAME", "cent_lon", "cent_lat"]].head(10))
    
    # Save updated shapefile
    out_shp = OUTPUT_DIR / "final_study_district.shp"
    print(f"\nSaving updated shapefile to {out_shp}...")
    gdf.to_file(out_shp)
    print("[SUCCESS] Shapefile saved to outputs.")
    
    # Copy to data folder to keep in sync
    print(f"Copying updated shapefile files to {DATA_DIR}...")
    for ext in ["shp", "shx", "dbf", "prj", "cpg"]:
        src = OUTPUT_DIR / f"final_study_district.{ext}"
        dst = DATA_DIR / f"final_study_district.{ext}"
        if src.exists():
            shutil.copy(src, dst)
            
    print("[SUCCESS] Centroid calculation completed.")

if __name__ == "__main__":
    main()
