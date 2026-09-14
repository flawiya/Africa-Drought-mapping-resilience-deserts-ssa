"""
generate_sfca_stats.py

Generates statistical comparison plots and a summary markdown table 
for the 2SFCA and 3SFCA road network results.
"""

import geopandas as gpd
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent  # repo root
OUTPUT_DIR = PROJECT / "dissertation_work" / "meeting_03_july" / "outputs"
INPUT_GPKG = OUTPUT_DIR / "districts_road_network_sfca_50km.gpkg"

# Load Data
print("Loading accessibility data...")
gdf = gpd.read_file(INPUT_GPKG)

# --- 1. Generate Statistical Plots ---
fig, axes = plt.subplots(1, 2, figsize=(16, 6))

# Plot A: Scatter Plot (How scores shift between models)
sns.scatterplot(
    data=gdf, 
    x="A_2SFCA_norm_50km", y="A_3SFCA_norm_50km", 
    alpha=0.6, color="#2980b9", s=60, ax=axes[0]
)
# Add perfect correlation line
max_val = max(gdf["A_2SFCA_norm_50km"].max(), gdf["A_3SFCA_norm_50km"].max())
axes[0].plot([0, max_val], [0, max_val], 'r--', label="1:1 Ratio (No Difference)")
axes[0].set_title("2SFCA vs 3SFCA Scores per District", fontsize=14, fontweight='bold')
axes[0].set_xlabel("2SFCA Score (No Competition)")
axes[0].set_ylabel("3SFCA Score (With Competition)")
axes[0].legend()

# Plot B: Histogram Distribution
sns.kdeplot(data=gdf, x="A_2SFCA_norm_50km", fill=True, alpha=0.4, label="2SFCA", color="#27ae60", ax=axes[1])
sns.kdeplot(data=gdf, x="A_3SFCA_norm_50km", fill=True, alpha=0.4, label="3SFCA", color="#8e44ad", ax=axes[1])
axes[1].set_title("Distribution of Accessibility Scores across Africa", fontsize=14, fontweight='bold')
axes[1].set_xlabel("Normalized Accessibility Score")
axes[1].set_ylabel("Density of Districts")
axes[1].legend()

plt.tight_layout()
out_plot = OUTPUT_DIR / "sfca_statistical_comparison.png"
plt.savefig(out_plot, dpi=300, bbox_inches='tight')
plt.close()
print(f"[SAVED] Statistical plots to {out_plot}")

# --- 2. Generate Summary Table (Markdown) ---
def classify_scores(series):
    # Classify into 5 tiers (excluding zeros)
    conditions = [
        (series == 0),
        (series > 0) & (series <= 0.2),
        (series > 0.2) & (series <= 0.4),
        (series > 0.4) & (series <= 0.6),
        (series > 0.6)
    ]
    choices = ["Zero Access (Food Desert)", "Low Access", "Moderate Access", "High Access", "Very High Access"]
    return np.select(conditions, choices, default="Unknown")

gdf["Category_2SFCA"] = classify_scores(gdf["A_2SFCA_norm_50km"])
gdf["Category_3SFCA"] = classify_scores(gdf["A_3SFCA_norm_50km"])

summary_2 = gdf["Category_2SFCA"].value_counts().reset_index()
summary_2.columns = ["Accessibility Tier", "Number of Districts (2SFCA)"]

summary_3 = gdf["Category_3SFCA"].value_counts().reset_index()
summary_3.columns = ["Accessibility Tier", "Number of Districts (3SFCA)"]

# Merge summaries
df_summary = pd.merge(summary_2, summary_3, on="Accessibility Tier", how="outer").fillna(0)
df_summary["Number of Districts (2SFCA)"] = df_summary["Number of Districts (2SFCA)"].astype(int)
df_summary["Number of Districts (3SFCA)"] = df_summary["Number of Districts (3SFCA)"].astype(int)

# Sort logically
order = {"Zero Access (Food Desert)": 1, "Low Access": 2, "Moderate Access": 3, "High Access": 4, "Very High Access": 5}
df_summary["sort_order"] = df_summary["Accessibility Tier"].map(order)
df_summary = df_summary.sort_values("sort_order").drop(columns=["sort_order"])

out_md = OUTPUT_DIR / "sfca_summary_table.md"
with open(out_md, "w") as f:
    f.write("# Accessibility Summary Table\n\n")
    f.write("This table shows the distribution of districts across different tiers of food market accessibility.\n\n")
    f.write(df_summary.to_markdown(index=False))

print(f"[SAVED] Summary table to {out_md}")
