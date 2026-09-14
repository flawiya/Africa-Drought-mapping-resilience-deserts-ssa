"""
Last Updated: 2026-06-30
script_04_bivariate_map.py
Combine drought cluster (hierarchical k=3) with 2SFCA accessibility (50 km)
into a 3x3 bivariate choropleth map.

Rows    = Drought Risk   (1=Low, 2=Moderate, 3=High)
Columns = Accessibility  (1=Low, 2=Moderate, 3=High)
Worst quadrant (high drought + low access) highlighted with annotation.
"""

import geopandas as gpd
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent  # repo root
GDF_PATH   = (PROJECT / "dissertation_work" / "meeting_25_june" /
              "outputs" / "districts_2sfca_accessibility.gpkg")
OUTPUT_DIR = PROJECT / "dissertation_work" / "meeting_25_june" / "outputs"

gdf = gpd.read_file(GDF_PATH).to_crs("EPSG:4326")

# Classify drought risk from cluster means
year_cols = [c for c in gdf.columns if c.startswith("drought_days_")]
if year_cols:
    gdf["mean_drought"] = gdf[year_cols].mean(axis=1)
else:
    gdf["mean_drought"] = 0

cluster_severity = gdf.groupby("hierarchical_k3")["mean_drought"].mean().rank()
gdf["drought_bin"] = gdf["hierarchical_k3"].map(cluster_severity.to_dict()).astype(int)

# Classify accessibility into 3 bins (handling high zero-inflation):
# Bin 1: No Access (score == 0)
# Bin 2: Low-Moderate (0 < score <= median of non-zero values)
# Bin 3: High Access (score > median of non-zero values)
non_zero = gdf[gdf["access_norm_50km"] > 0]["access_norm_50km"]
med_val = non_zero.median() if len(non_zero) > 0 else 0.5
print(f"Non-zero accessibility median: {med_val:.6f}")

def bin_access(val):
    if val <= 0:
        return 1
    elif val <= med_val:
        return 2
    else:
        return 3

gdf["access_bin"] = gdf["access_norm_50km"].apply(bin_access)
gdf["biv_class"] = gdf["drought_bin"].astype(str) + "-" + gdf["access_bin"].astype(str)

# 3x3 bivariate palette (drought row x access column)
biv_palette = {
    "1-1": "#e8e8e8",
    "1-2": "#ace4e4",
    "1-3": "#5ac8c8",
    "2-1": "#dfb0d6",
    "2-2": "#a5add3",
    "2-3": "#5698b9",
    "3-1": "#be64ac",   # HIGH drought, LOW access -> worst
    "3-2": "#8c62aa",
    "3-3": "#3b4994",
}
gdf["color"] = gdf["biv_class"].map(biv_palette).fillna("#cccccc")

fig, ax = plt.subplots(figsize=(14, 13))
fig.patch.set_facecolor("#F0F0F0")
gdf.plot(color=gdf["color"], ax=ax, linewidth=0.25,
         edgecolor="#666666", alpha=0.9)

ax.set_title(
    "Agricultural Drought Risk x Market Accessibility in Africa\n"
    "Hierarchical Clustering (k=3) x 2SFCA (50 km catchment)",
    fontsize=14, fontweight="bold", pad=15
)
ax.axis("off")

# 3x3 legend inset
leg_ax = fig.add_axes([0.07, 0.07, 0.20, 0.20])
leg_ax.set_xlim(0, 3); leg_ax.set_ylim(0, 3)
leg_ax.set_facecolor("#F0F0F0")
for d in [1, 2, 3]:
    for a in [1, 2, 3]:
        key   = f"{d}-{a}"
        color = biv_palette.get(key, "#cccccc")
        rect  = mpatches.FancyBboxPatch(
            (a-1, d-1), 1, 1,
            boxstyle="square,pad=0",
            facecolor=color, edgecolor="white", linewidth=1.0
        )
        leg_ax.add_patch(rect)

leg_ax.set_xticks([0.5, 1.5, 2.5])
leg_ax.set_xticklabels(["Low", "Mod", "High"], fontsize=8)
leg_ax.set_yticks([0.5, 1.5, 2.5])
leg_ax.set_yticklabels(["Low", "Mod", "High"], fontsize=8)
leg_ax.set_xlabel("Accessibility", fontsize=9, labelpad=4)
leg_ax.set_ylabel("Drought Risk", fontsize=9, labelpad=4)
leg_ax.set_title("Legend", fontsize=9, fontweight="bold")
# Mark worst quadrant
leg_ax.text(0.5, 2.5, "Worst", ha="center", va="center",
            fontsize=7, color="white", fontweight="bold")

plt.tight_layout()
out = OUTPUT_DIR / "bivariate_drought_accessibility_map.png"
plt.savefig(out, dpi=200, bbox_inches="tight")
plt.show()
print(f"[SAVED] {out}")

print("\nDistrict counts per bivariate class:")
print(gdf["biv_class"].value_counts().sort_index())

print("\nWorst districts (3-1: High Drought + Low Access):")
worst = gdf[gdf["biv_class"] == "3-1"][
    ["COUNTRY","ADM_NAME","access_norm_50km","mean_drought"]
].sort_values("mean_drought", ascending=False)
print(worst.head(20).to_string())
out_csv = OUTPUT_DIR / "worst_districts_high_drought_low_access.csv"
worst.to_csv(out_csv, index=False)
print(f"[SAVED] {out_csv}")
