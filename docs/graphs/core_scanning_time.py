import pandas as pd
import matplotlib.pyplot as plt

# Read data
df = pd.read_csv("scanning_time_data.csv")

# Compute total time
df["total_time_min"] = (
    df["scanning_time_min"] +
    df["stitching_time_min"]
)

# Sort by sample length
df = df.sort_values("sample_length_mm")

# Create plot
fig, ax = plt.subplots(figsize=(8, 5))

ax.plot(
    df["sample_length_mm"],
    df["total_time_min"],
    marker="o",
    linewidth=2,
    markersize=6,
    color="black"
)

ax.set_xlabel("Sample Length (mm)")
ax.set_ylabel("Digitization Time (minutes)")
ax.set_title("Sample Length vs. Digitization Time")

ax.grid(True, alpha=0.3)

plt.tight_layout()

# Save figure
plt.savefig("scanning_time.png", dpi=300)
plt.show()