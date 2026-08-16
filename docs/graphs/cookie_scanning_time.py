import pandas as pd
import matplotlib.pyplot as plt

# Read data
df = pd.read_csv("cookie_scanning_time_data.csv")

# Total digitization time
df["total_time_min"] = (
    df["scanning_time_min"]
    + df["stitching_time_min"]
)

# Sort by area
df = df.sort_values("sample_area_mm2")

# Plot
fig, ax = plt.subplots(figsize=(8, 5))

ax.plot(
    df["sample_area_mm2"],
    df["total_time_min"],
    marker="s",
    linewidth=2,
    markersize=6,
    color="black"
)

ax.set_xlabel("Sample Area (mm²)")
ax.set_ylabel("Digitization Time (minutes)")
ax.set_title("Cookie Sample Area vs. Digitization Time")

ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig("cookie_scanning_time.png", dpi=300)
plt.show()