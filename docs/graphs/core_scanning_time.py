import pandas as pd
import matplotlib.pyplot as plt

# --------------------------
# Matplotlib settings
# --------------------------

plt.rcParams.update({
    "font.size": 24,
    "axes.labelsize": 28,
    "xtick.labelsize": 22,
    "ytick.labelsize": 22,
    "legend.fontsize": 22
})

# --------------------------
# Read data
# --------------------------

df = pd.read_csv("core_scanning_time_data.csv")

df = df[df["sample_length_mm"] < 300] 
df = df[df["sample_length_mm"] > 50] 

df["stitching_time_min"] = df["stitching_time_sec"] / 60
df["scanning_time_min"] = df["scanning_time_sec"] / 60

# Calculate total time
df["total_time_min"] = (
    df["scanning_time_min"] +
    df["stitching_time_min"]
)

# Sort by sample length
df = df.sort_values("sample_length_mm")

# --------------------------
# Plot
# --------------------------

fig, ax = plt.subplots(figsize=(8, 6))

ax.plot(
    df["sample_length_mm"],
    df["total_time_min"],
    marker="o",
    linewidth=2.5,
    markersize=8,
    color="black"
)

ax.set_xlabel("Sample Length (mm)")
ax.set_ylabel("Digitization Time (min)")

ax.grid(True, alpha=0.3)

plt.tight_layout()

plt.savefig(
    "core_scanning_time.png",
    dpi=600,
    bbox_inches="tight"
)

plt.show()