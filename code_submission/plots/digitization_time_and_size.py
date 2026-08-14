import matplotlib.pyplot as plt

# Fake data points
time_minutes = [11, 43.6, 94.5, 120.3, 145.3, 149.6, 325.4]  # Time in minutes
sample_size_mm2 = [660, 1225, 1225, 1517, 1849, 1980, 4200]  # Sample size in mm^2
stitch_time_minutes = [0.4, 1.29, 2.98, 3.65, 4.32, 5.14, 10.28]

# Create the plot
plt.figure(figsize=(8, 6))
plt.plot(time_minutes, sample_size_mm2, marker='o', linestyle='-', color='b', label = "Imaging Time")
plt.plot(stitch_time_minutes, sample_size_mm2, marker = "x", color = 'r', label = "30% Downscale Stitching Time")
# Add labels and title
plt.xlabel('Time (minutes)', fontsize=12)
plt.ylabel('Sample Size (mm$^2$)', fontsize=12)
plt.title('Time to Digitize Samples by Surface Area', fontsize=14)

# Add grid and legend
plt.grid(True, linestyle='--', alpha=0.7)
plt.legend(fontsize=12)

plt.savefig("./time_and_area.png")

# Show the plot
plt.tight_layout()
plt.show()