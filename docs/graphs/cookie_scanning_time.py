import pandas as pd
import matplotlib.pyplot as plt

plt.rcParams.update({
    "font.size": 16,
    "axes.labelsize": 18,
    "xtick.labelsize": 16,
    "ytick.labelsize": 16,
    "legend.fontsize": 16
})

df = pd.read_csv("cookie_scanning_time_data.csv")

df["total_time_min"] = (
    df["scanning_time_min"]
    + df["stitching_time_min"]
)

df = df.sort_values("sample_area_mm2")

fig, ax = plt.subplots(figsize=(8, 6))

ax.plot(
    df["sample_area_mm2"],
    df["total_time_min"],
    marker="s",
    linewidth=2.5,
    markersize=8,
    color="black"
)

ax.set_xlabel("Sample Area (mm²)")
ax.set_ylabel("Digitization Time (min)")

ax.grid(True, alpha=0.3)

plt.tight_layout()

plt.savefig(
    "cookie_scanning_time.png",
    dpi=600,
    bbox_inches="tight"
)

plt.show()