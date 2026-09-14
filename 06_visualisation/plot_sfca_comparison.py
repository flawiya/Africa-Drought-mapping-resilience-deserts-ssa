"""
Compare 2SFCA (Road) vs 3SFCA (Road).
"""
import geopandas as gpd
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent  # repo root
OUTPUT_DIR = PROJECT / "dissertation_work" / "meeting_03_july" / "outputs"

gdf_sfca = gpd.read_file(OUTPUT_DIR / "districts_road_network_sfca.gpkg")

def classify_quantile(series, n_classes=5):
    mask = series > 0
    labels = np.zeros(len(series), dtype=int)
    if mask.sum() > 0:
        quantiles = np.percentile(series[mask], [20, 40, 60, 80])
        for i, q in enumerate(quantiles):
            labels[mask & (series > q)] = i + 1
        labels[mask & (labels == 0)] = 1
    return labels

fig, axes = plt.subplots(1, 2, figsize=(20, 10))
fig.patch.set_facecolor('white')

colors_list = ['#d0d0d0', '#2ecc71', '#f1c40f', '#e67e22', '#e74c3c', '#8e44ad']
class_labels = ['No Access (0)', 'Very Low', 'Low', 'Moderate', 'High', 'Very High']
cmap = mcolors.ListedColormap(colors_list)
bounds = [-0.5, 0.5, 1.5, 2.5, 3.5, 4.5, 5.5]
norm = mcolors.BoundaryNorm(bounds, cmap.N)

# 2SFCA
gdf_sfca['class_2'] = classify_quantile(gdf_sfca['A_2SFCA_norm'])
ax1 = axes[0]
gdf_sfca.plot(column='class_2', ax=ax1, cmap=cmap, norm=norm, edgecolor='#888', linewidth=0.3)
ax1.set_title(f"2SFCA Accessibility (Road Network)\nZero-access: {int((gdf_sfca['A_2SFCA']==0).sum())} districts", fontsize=14, fontweight='bold')
ax1.axis('off')

# 3SFCA
gdf_sfca['class_3'] = classify_quantile(gdf_sfca['A_3SFCA_norm'])
ax2 = axes[1]
gdf_sfca.plot(column='class_3', ax=ax2, cmap=cmap, norm=norm, edgecolor='#888', linewidth=0.3)
ax2.set_title(f"3SFCA Accessibility (Road Network + Competition Weights)\nZero-access: {int((gdf_sfca['A_3SFCA']==0).sum())} districts", fontsize=14, fontweight='bold')
ax2.axis('off')

from matplotlib.patches import Patch
legend_elements = [Patch(facecolor=c, edgecolor='#888', label=l) for c, l in zip(colors_list, class_labels)]
fig.legend(handles=legend_elements, loc='lower center', ncol=6, fontsize=11, frameon=True, bbox_to_anchor=(0.5, 0.02))
fig.suptitle("Comparison of 2SFCA vs 3SFCA Food Market Accessibility (Road Network)", fontsize=16, fontweight='bold', y=0.98)

plt.tight_layout(rect=[0, 0.08, 1, 0.95])
out1 = OUTPUT_DIR / "road_network_2sfca_vs_3sfca_comparison_map.png"
plt.savefig(out1, dpi=300, bbox_inches='tight')
plt.close()
print(f"[SAVED] {out1}")
