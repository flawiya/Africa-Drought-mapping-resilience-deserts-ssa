"""
Plot POIs on an interactive Folium map overlaid on district boundaries
coloured by the reference hierarchical K=3 clusters.

Outputs:
  - outputs/pois_on_districts_map.html   (interactive Folium map)
  - outputs/pois_on_districts_map.png    (static matplotlib map)
"""

import sys
import pandas as pd
import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path
import folium
from folium.plugins import MarkerCluster

# ── Paths ────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent  # repo root
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "outputs"

_shp = DATA_DIR / "final_study_district.shp"
if not _shp.exists():
    _shp = OUTPUT_DIR / "final_study_district.shp"
SHP_FILE = _shp

_poi_csv = DATA_DIR / "africa_354_classified_pois.csv"
if not _poi_csv.exists():
    _poi_csv = OUTPUT_DIR / "africa_354_classified_pois.csv"
POI_CSV = _poi_csv

MAP_HTML = OUTPUT_DIR / "pois_on_districts_map.html"
MAP_PNG  = OUTPUT_DIR / "pois_on_districts_map.png"

# ── Colour palettes ─────────────────────────────────────────────────────────
# District clusters (hc_k3: 0, 1, 2)
CLUSTER_COLORS = {
    0: "#27ae60",  # Green  – Cluster 1: Moderate (Kenya, Uganda, Egypt)
    1: "#f39c12",  # Orange – Cluster 2: High (Tanzania, Zambia, Burundi)
    2: "#c0392b",  # Red    – Cluster 3: High (Malawi, Mozambique, Swaziland)
}
CLUSTER_LABELS = {
    0: "Cluster 1: Moderate (Kenya, Uganda, Egypt)",
    1: "Cluster 2: High (Tanzania, Zambia, Burundi)",
    2: "Cluster 3: High (Malawi, Mozambique, Swaziland)",
}

# POI classes → marker colour + icon
POI_STYLE = {
    "Agricultural Output (Market Access)": {
        "color": "green",
        "icon": "shopping-cart",
        "prefix": "fa",
    },
    "Financial Accessibility": {
        "color": "blue",
        "icon": "university",
        "prefix": "fa",
    },
    "Post-Harvest & Processing (Logistics)": {
        "color": "orange",
        "icon": "truck",
        "prefix": "fa",
    },
    "Agricultural Input (Drought Mitigation)": {
        "color": "red",
        "icon": "leaf",
        "prefix": "fa",
    },
}


def main():
    print("--- PLOTTING POIs ON DISTRICT MAP ---")

    # 1. Load data -------------------------------------------------------
    if not SHP_FILE.exists():
        print(f"[ERROR] Shapefile not found: {SHP_FILE}")
        sys.exit(1)
    if not POI_CSV.exists():
        print(f"[ERROR] POI CSV not found: {POI_CSV}")
        sys.exit(1)

    gdf = gpd.read_file(SHP_FILE)
    df_pois = pd.read_csv(POI_CSV)
    print(f"Loaded {len(gdf)} districts and {len(df_pois)} POIs.")

    # 2. Prepare district GeoDataFrame (WGS84, simplified) --------------
    gdf_wgs = gdf.to_crs(epsg=4326)
    gdf_wgs["geometry"] = gdf_wgs["geometry"].simplify(
        tolerance=0.01, preserve_topology=True
    )
    gdf_wgs["cluster_label"] = gdf_wgs["hc_k3"].map(CLUSTER_LABELS)

    # 3. Build the Folium map --------------------------------------------
    # Centre on Africa
    center_lat = gdf_wgs.geometry.centroid.y.mean()
    center_lon = gdf_wgs.geometry.centroid.x.mean()
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=4,
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}",
        attr="Tiles &copy; Esri",
    )

    # 3a. District choropleth layer -------------------------------------
    def style_function(feature):
        cluster_id = feature["properties"]["hc_k3"]
        return {
            "fillColor": CLUSTER_COLORS.get(cluster_id, "#cccccc"),
            "color": "black",
            "weight": 0.4,
            "fillOpacity": 0.45,
        }

    def highlight_function(feature):
        return {
            "weight": 2,
            "color": "#333",
            "fillOpacity": 0.65,
        }

    # Build tooltip fields
    tooltip_fields = ["COUNTRY", "ADM_NAME", "cluster_label"]
    tooltip_aliases = ["Country:", "District:", "Cluster:"]

    folium.GeoJson(
        gdf_wgs.__geo_interface__,
        name="District Clusters (K=3)",
        style_function=style_function,
        highlight_function=highlight_function,
        tooltip=folium.GeoJsonTooltip(
            fields=tooltip_fields,
            aliases=tooltip_aliases,
            sticky=True,
        ),
    ).add_to(m)

    # 3b. POI markers with MarkerCluster per class ----------------------
    print("Adding POI markers...")
    for poi_class, style in POI_STYLE.items():
        subset = df_pois[df_pois["poi_class"] == poi_class]
        if subset.empty:
            continue

        mc = MarkerCluster(name=f"POI: {poi_class}", show=True)

        for _, row in subset.iterrows():
            popup_text = (
                f"<b>{row.get('name', 'Unnamed')}</b><br>"
                f"<i>{poi_class}</i><br>"
                f"Lat: {row['lat']:.4f}, Lon: {row['lon']:.4f}"
            )
            folium.Marker(
                location=[row["lat"], row["lon"]],
                popup=folium.Popup(popup_text, max_width=250),
                tooltip=row.get("name", poi_class),
                icon=folium.Icon(
                    color=style["color"],
                    icon=style["icon"],
                    prefix=style["prefix"],
                ),
            ).add_to(mc)

        mc.add_to(m)
        print(f"  {poi_class}: {len(subset)} markers added.")

    # 3c. Add a legend (HTML overlay) -----------------------------------
    legend_html = """
    <div style="
        position: fixed; bottom: 30px; left: 30px;
        background: white; padding: 14px 18px;
        border: 2px solid #555; border-radius: 8px;
        z-index: 9999; font-size: 13px; line-height: 1.8;
        box-shadow: 2px 2px 6px rgba(0,0,0,0.3);
        max-width: 320px;
    ">
    <b style="font-size:14px;">Legend</b><br>
    <b>District Clusters</b><br>
    <i style="background:#27ae60;width:14px;height:14px;display:inline-block;border:1px solid #333;"></i> Cluster 1: Moderate<br>
    <i style="background:#f39c12;width:14px;height:14px;display:inline-block;border:1px solid #333;"></i> Cluster 2: High (Tanzania/Zambia)<br>
    <i style="background:#c0392b;width:14px;height:14px;display:inline-block;border:1px solid #333;"></i> Cluster 3: High (Malawi/Mozambique)<br>
    <hr style="margin:4px 0;">
    <b>POI Classes</b><br>
    <i class="fa fa-shopping-cart" style="color:green;"></i> Agricultural Output (Market)<br>
    <i class="fa fa-university" style="color:blue;"></i> Financial Accessibility<br>
    <i class="fa fa-truck" style="color:orange;"></i> Post-Harvest & Processing<br>
    <i class="fa fa-leaf" style="color:red;"></i> Agricultural Input (Drought)<br>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    # Layer control toggle
    folium.LayerControl(collapsed=False).add_to(m)

    # Save
    m.save(str(MAP_HTML))
    print(f"\n[SUCCESS] Interactive map saved --> {MAP_HTML}")

    # 4. Static matplotlib map ------------------------------------------
    print("Generating static PNG map...")
    gdf_proj = gdf.to_crs("ESRI:102022")

    # Convert POIs to GeoDataFrame and project
    gdf_pois = gpd.GeoDataFrame(
        df_pois,
        geometry=gpd.points_from_xy(df_pois["lon"], df_pois["lat"]),
        crs="EPSG:4326",
    ).to_crs("ESRI:102022")

    fig, ax = plt.subplots(figsize=(12, 12))

    # Plot district polygons
    for cid, color in CLUSTER_COLORS.items():
        sub = gdf_proj[gdf_proj["hc_k3"] == cid]
        if not sub.empty:
            sub.plot(ax=ax, color=color, edgecolor="black", linewidth=0.2, alpha=0.5)

    # Plot POIs by class
    poi_marker_colors = {
        "Agricultural Output (Market Access)": "#2ecc71",
        "Financial Accessibility": "#3498db",
        "Post-Harvest & Processing (Logistics)": "#e67e22",
        "Agricultural Input (Drought Mitigation)": "#e74c3c",
    }
    poi_markers = {
        "Agricultural Output (Market Access)": "o",
        "Financial Accessibility": "s",
        "Post-Harvest & Processing (Logistics)": "^",
        "Agricultural Input (Drought Mitigation)": "D",
    }

    for poi_class, color in poi_marker_colors.items():
        sub = gdf_pois[gdf_pois["poi_class"] == poi_class]
        if not sub.empty:
            sub.plot(
                ax=ax,
                color=color,
                marker=poi_markers[poi_class],
                markersize=12,
                alpha=0.8,
                edgecolor="black",
                linewidth=0.3,
                label=poi_class,
            )

    ax.set_title(
        "POIs on Drought Vulnerability Districts (K = 3 Clusters)\n"
        "Refined 354 Districts in Africa",
        fontsize=13,
        fontweight="bold",
        pad=15,
    )

    # Build legend
    handles = []
    for cid, color in CLUSTER_COLORS.items():
        handles.append(
            mpatches.Patch(color=color, alpha=0.5, label=CLUSTER_LABELS[cid])
        )
    for poi_class, color in poi_marker_colors.items():
        short_label = poi_class.split("(")[0].strip()
        handles.append(
            plt.Line2D(
                [0], [0],
                marker=poi_markers[poi_class],
                color="w",
                markerfacecolor=color,
                markeredgecolor="black",
                markersize=8,
                label=short_label,
            )
        )

    ax.legend(handles=handles, loc="lower left", fontsize=8, frameon=True,
              facecolor="white", ncol=1)
    ax.set_axis_off()
    plt.tight_layout()
    plt.savefig(MAP_PNG, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"[SUCCESS] Static map saved --> {MAP_PNG}")

    print("\n--- DONE ---")


if __name__ == "__main__":
    main()
