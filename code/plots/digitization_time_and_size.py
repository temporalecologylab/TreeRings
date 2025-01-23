import matplotlib.pyplot as plt

# Fake data points
time_minutes = [0, 10, 20, 30, 40]  # Time in minutes
sample_size_mm2 = [5, 15, 30, 50, 80]  # Sample size in mm^2

# Create the plot
plt.figure(figsize=(8, 6))
plt.plot(time_minutes, sample_size_mm2, marker='o', linestyle='-', color='b')

# Add labels and title
plt.xlabel('Time (minutes)', fontsize=12)
plt.ylabel('Sample Size (mm$^2$)', fontsize=12)
plt.title('Time vs Sample Size', fontsize=14)

# Add grid and legend
plt.grid(True, linestyle='--', alpha=0.7)
plt.legend(fontsize=12)

plt.savefig("./time_and_area.png")

# Show the plot
plt.tight_layout()
plt.show()