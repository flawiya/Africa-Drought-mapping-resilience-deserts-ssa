"""
script_01_temporal_trajectories.py
Plot temporal drought trajectories for the refined 361 districts,
one subplot per cluster (hierarchical k=3).
Each subplot shows all individual district drought-day time series (faint lines),
bold cluster-mean line, and plus-minus 1 std shaded band.
"""

import matplotlib
matplotlib.use("Agg")
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent  # repo root
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR  = PROJECT_ROOT / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

_csv = DATA_DIR / "final_spatial_clusters.csv"
if not _csv.exists():
    _csv = OUTPUT_DIR / "final_spatial_clusters.csv"
RESULTS_CSV = _csv

df = pd.read_csv(RESULTS_CSV)
year_cols = [c for c in df.columns if c.startswith("drought_days_")]
# The new CSV doesn't have the individual year cols inside it. 
# It only has spatial_k3, mean_drought, etc. 
# Wait! I need to fix the input to the temporal trajectories.

cluster_means_per_cluster = df.groupby("cluster_label")[year_cols].mean().mean(axis=1)
sorted_clusters = cluster_means_per_cluster.sort_values().index.tolist()
risk_labels = {
    sorted_clusters[0]: "Low Vulnerability",
    sorted_clusters[1]: "Moderate Vulnerability",
    sorted_clusters[2]: "High Vulnerability",
}
df["risk_label"] = df["cluster_label"].map(risk_labels)

print("Cluster composition:")
print(df.groupby(["cluster_label", "risk_label"]).size().reset_index(name="n_districts"))

COLORS = {
    "Low Vulnerability":      "#2A9D8F",
    "Moderate Vulnerability": "#F4A261",
    "High Vulnerability":     "#E63946",
}

fig, axes = plt.subplots(1, 3, figsize=(20, 6), sharey=True)
fig.patch.set_facecolor("#FAFAFA")

for ax, c_id in zip(axes, sorted_clusters):
    risk  = risk_labels[c_id]
    color = COLORS[risk]
    mask  = df["cluster_label"] == c_id
    n     = mask.sum()
    X     = df.loc[mask, year_cols].values
    mean_ts = X.mean(axis=0)
    std_ts  = X.std(axis=0)

    for row in X:
        ax.plot(years, row, color=color, alpha=0.10, linewidth=0.5)

    ax.fill_between(years, mean_ts - std_ts, mean_ts + std_ts,
                    color=color, alpha=0.18, zorder=3)
    ax.plot(years, mean_ts, color=color, linewidth=2.6, zorder=5, label="Cluster mean")

    ax.set_title(f"Cluster {c_id}  -  {risk}\n({n} districts)",
                 fontsize=12, fontweight="bold", color=color, pad=8)
    ax.set_xlabel("Year", fontsize=10)
    ax.tick_params(axis="x", rotation=45, labelsize=8)
    ax.tick_params(axis="y", labelsize=9)
    ax.grid(linestyle="--", alpha=0.35, color="grey")
    ax.set_facecolor("#F8F8F8")
    ax.spines[["top","right"]].set_visible(False)
    ax.legend(fontsize=9, loc="upper left")

axes[0].set_ylabel("Drought Days per Crop Year", fontsize=11)
fig.suptitle(
    "Temporal Drought Trajectories by Hierarchical Cluster (k = 3)\n"
    "Refined 361 Maize-Dominant Districts in Africa",
    fontsize=13, fontweight="bold", y=1.02
)

plt.tight_layout()
out = OUTPUT_DIR / "cluster_temporal_trajectories.png"
plt.savefig(out, dpi=200, bbox_inches="tight")
plt.close()
print(f"\n[SAVED] {out}")
