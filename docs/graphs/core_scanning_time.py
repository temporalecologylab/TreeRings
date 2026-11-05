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

df = pd.read_csv("core_scanning_times_2.csv")

# df = df[df["sample_length_mm"] > 50] 


df["stitching_time_min"] = df["stitching_time_s"] / 60
df["scanning_time_min"] = df["scanning_time_s"] / 60

# Calculate total time
df["total_time_min"] = (
    df["scanning_time_min"] +
    df["stitching_time_min"]
)


# --------------------------
# Plot
# --------------------------

fig, ax = plt.subplots(figsize=(8, 6))

sc = ax.scatter(
    x = df["sample_length_dpi_conversion_mm"],
    y = df["total_time_min"],
    c=df["percent_overlap"],
    cmap = "viridis",
    vmin = 30,
    vmax = 90,
    s= 15)

ax.set_xlabel("Sample Length (mm)")
ax.set_ylabel("Digitization Time (min)")

ax.grid(True, alpha=0.3)
cbar = plt.colorbar(sc, ax=ax)
cbar.set_label("Percent Overlap (%)")

plt.tight_layout()

plt.savefig(
    "core_scanning_time.png",
    dpi=600,
    bbox_inches="tight"
)

plt.show()