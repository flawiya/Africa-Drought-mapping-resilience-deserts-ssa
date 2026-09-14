"""
download_all_africa_pois.py
Download food-system POIs from Overpass API for ALL 51 African countries
defined in data/africa_admx.shp.
- Saves progress incrementally in scratch/pois_download_scratch.json so it can resume if interrupted.
- Performs spatial clipping using country boundaries to prevent bounding box overlap duplicates.
- De-duplicates by OSM ID.
- Overwrites the existing GPKG & Shapefile with the updated deduplicated dataset.
"""
import requests
import geopandas as gpd
import pandas as pd
import json
import time
from shapely.geometry import Point, shape
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent  # repo root
AFRICA_SHP   = PROJECT / "data" / "africa_admx.shp"
OUTPUT_DIR   = PROJECT / "dissertation_work" / "meeting_25_june" / "outputs"
SCRATCH_DIR  = PROJECT / "dissertation_work" / "meeting_25_june" / "scratch"
SCRATCH_DIR.mkdir(parents=True, exist_ok=True)

SCRATCH_JSON = SCRATCH_DIR / "pois_download_scratch.json"
OUT_GPKG     = OUTPUT_DIR / "pois_food_system_africa.gpkg"
OUT_SHP_DIR  = OUTPUT_DIR / "pois_food_system_africa_shp"
OUT_SHP_DIR.mkdir(exist_ok=True)
OUT_SHP      = OUT_SHP_DIR / "pois_food_system_africa.shp"

# ── Load Africa countries ─────────────────────────────────────────────────────
print("Loading Africa administrative boundaries...")
gdf_africa = gpd.read_file(AFRICA_SHP).to_crs(4326)
countries = sorted(gdf_africa["COUNTRY"].dropna().unique().tolist())
print(f"Total countries to query: {len(countries)}\n")

# ── Overpass endpoints ────────────────────────────────────────────────────────
ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://lz4.overpass-api.de/api/interpreter",
]

HEADERS = {
    "User-Agent": "Africa-Drought-Study-Global/2.0 (dissertation research)",
    "Accept":     "application/json",
}

# ── OSM tag filters ───────────────────────────────────────────────────────────
TAGS = {
    "market":          [("amenity","marketplace")],
    "supermarket":     [("shop","supermarket")],
    "convenience":     [("shop","convenience"),("shop","grocery"),("shop","general")],
    "agri_supply":     [("shop","agrarian"),("shop","farm"),("shop","garden_centre")],
    "wholesale":       [("shop","wholesale")],
    "bank":            [("amenity","bank")],
    "microfinance":    [("amenity","microfinance"),("amenity","mobile_money")],
    "bus_station":     [("amenity","bus_station")],
    "fuel_logistics":  [("amenity","fuel")],
}

def build_query(s, w, n, e):
    bb = f"{s:.4f},{w:.4f},{n:.4f},{e:.4f}"
    parts = []
    for cat, pairs in TAGS.items():
        for key, val in pairs:
            parts.append(f'  node["{key}"="{val}"]({bb});')
            parts.append(f'  way["{key}"="{val}"]({bb});')
    return "[out:json][timeout:120];\n(\n" + "\n".join(parts) + "\n);\nout center tags;"

def get_category(tags):
    for cat, pairs in TAGS.items():
        for key, val in pairs:
            if tags.get(key) == val:
                return cat
    return "other"

def query_overpass(query, label):
    for ep in ENDPOINTS:
        for attempt in range(1, 4):
            try:
                r = requests.get(ep, params={"data": query}, headers=HEADERS, timeout=120)
                if r.status_code == 200:
                    return r.json().get("elements", [])
                elif r.status_code in (429, 503):
                    wait = 30 * attempt
                    print(f"    [{r.status_code}] {ep} rate limited - waiting {wait}s...")
                    time.sleep(wait)
                else:
                    print(f"    [HTTP {r.status_code}] {ep} failed")
                    break
            except requests.Timeout:
                print(f"    [timeout] {ep} attempt {attempt}")
                time.sleep(15)
            except Exception as ex:
                print(f"    [error] {ep}: {ex}")
                break
    return []

# ── Load progress from scratch ────────────────────────────────────────────────
progress = {}
if SCRATCH_JSON.exists():
    try:
        progress = json.loads(SCRATCH_JSON.read_text(encoding="utf-8"))
        print(f"Loaded progress from scratch. {len(progress)} countries already completed.")
    except Exception as e:
        print(f"Failed to load scratch file: {e}. Starting fresh.")

# ── Query countries ───────────────────────────────────────────────────────────
for i, country in enumerate(countries, 1):
    if country in progress:
        print(f"[{i:02d}/{len(countries)}] {country} already completed. (POIs: {len(progress[country])})")
        continue

    # Filter country boundaries
    cty_gdf = gdf_africa[gdf_africa["COUNTRY"] == country]
    if cty_gdf.empty:
        continue
    
    cty_geom = cty_gdf.geometry.iloc[0]
    b = cty_gdf.total_bounds  # minx, miny, maxx, maxy
    s, w, n, e = b[1] - 0.1, b[0] - 0.1, b[3] + 0.1, b[2] + 0.1
    
    print(f"[{i:02d}/{len(countries)}] Querying {country}...")
    query = build_query(s, w, n, e)
    elements = query_overpass(query, country)
    print(f"         -> {len(elements):,} raw elements from Overpass")
    
    cty_records = []
    for el in elements:
        lat = el.get("lat") or (el.get("center") or {}).get("lat")
        lon = el.get("lon") or (el.get("center") or {}).get("lon")
        if lat is None or lon is None:
            continue
        
        # Spatial boundary check (must fall inside country geometry)
        pt = Point(lon, lat)
        if not pt.within(cty_geom):
            continue
            
        tags = el.get("tags", {})
        cty_records.append({
            "osm_id":   el.get("id"),
            "name":     tags.get("name", ""),
            "category": get_category(tags),
            "country":  country,
            "lat":      round(lat, 6),
            "lon":      round(lon, 6),
        })
        
    progress[country] = cty_records
    print(f"         -> {len(cty_records):,} validated POIs inside country boundary")
    
    # Save progress incrementally
    SCRATCH_JSON.write_text(json.dumps(progress, indent=2), encoding="utf-8")
    
    # Sleep to avoid rate limiting
    time.sleep(3)

# ── Merge and Save Final Datasets ─────────────────────────────────────────────
print("\nCombining all country records...")
all_records = []
for cty, recs in progress.items():
    all_records.extend(recs)

print(f"Total raw merged records: {len(all_records):,}")
if not all_records:
    print("Error: No POIs found at all!")
    exit(1)

# Deduplicate by OSM ID
df = pd.DataFrame(all_records).drop_duplicates(subset=["osm_id"], keep="first")
df["geometry"] = [Point(r.lon, r.lat) for r in df.itertuples()]
gdf_poi = gpd.GeoDataFrame(df, geometry="geometry", crs="EPSG:4326")

print(f"Deduplicated total POIs for all of Africa: {len(gdf_poi):,}")

# Save to GPKG
gdf_poi.to_file(OUT_GPKG, driver="GPKG")
print(f"[SAVED] {OUT_GPKG}")

# Save to Shapefile
gdf_poi.to_file(OUT_SHP, driver="ESRI Shapefile")
print(f"[SAVED] {OUT_SHP}")

# Clean up scratch progress file if completed successfully
if len(progress) == len(countries):
    try:
        SCRATCH_JSON.unlink()
        print("Completed successfully! Scratch progress file cleaned.")
    except Exception:
        pass

print("\nDone! POIs for all of Africa have been updated and saved.")
