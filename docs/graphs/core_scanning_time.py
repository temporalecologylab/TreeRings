import pandas as pd
import matplotlib.pyplot as plt

# --------------------------
# Matplotlib settings
# --------------------------

plt.rcParams.update({
    "font.size": 16,
    "axes.labelsize": 18,
    "xtick.labelsize": 16,
    "ytick.labelsize": 16,
    "legend.fontsize": 16
})

# --------------------------
# Read data
# --------------------------

df = pd.read_csv("core_scanning_time_data.csv")

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