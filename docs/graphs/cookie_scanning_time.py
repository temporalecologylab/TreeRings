import pandas as pd
import matplotlib.pyplot as plt

plt.rcParams.update({
    "font.size": 24,
    "axes.labelsize": 28,
    "xtick.labelsize": 22,
    "ytick.labelsize": 22,
    "legend.fontsize": 22
})

df = pd.read_csv("cookie_scanning_times_2.csv")

df["total_time_min"] = (
    df["scanning_time_s"] / 60
    + df["stitching_time_s"] / 60
)

df = df.sort_values("sample_area_mm2")

fig, ax = plt.subplots(figsize=(8, 6))

sc = ax.scatter(
    x = df["sample_area_mm2"],
    y = df["total_time_min"],
    c = df["percent_overlap"],
    cmap = "viridis",
    vmin = 30,
    vmax = 90,
    s= 15)


ax.set_xlabel("Sample Area (mm²)")
ax.set_ylabel("Digitization Time (min)")

cbar = plt.colorbar(sc, ax=ax)
cbar.set_label("Percent Overlap (%)")

ax.grid(True, alpha=0.3)

plt.tight_layout()

plt.savefig(
    "cookie_scanning_time.png",
    dpi=600,
    bbox_inches="tight"
)

plt.show()