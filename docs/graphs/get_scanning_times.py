from pathlib import Path
import json
import csv

root_dir = Path("./cookies_metadata")

rows = []

for json_file in root_dir.rglob("*.json"):
    try:
        with open(json_file, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        # sample_area_mm2,scanning_time_min,stitching_time_min
        rows.append([
            round(metadata["sample_height_mm"] * metadata["sample_width_mm"]),
            round(metadata["imaging_time"] / 60),
            round(metadata["stitching_time"] / 60),
        ])

    except Exception as e:
        print(f"Failed to process {json_file}: {e}")

with open("results.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow([
        "sample_area_mm2",
        "scanning_time_min",
        "stitching_time_min",
    ])
    writer.writerows(rows)