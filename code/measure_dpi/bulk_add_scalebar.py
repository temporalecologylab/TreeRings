# Generated with ChatGPT-4.0

from pathlib import Path

from add_scalebar import add_scale_bar


ROOT_DIR = Path(
    r"D:\representative_scans"
)


def main():

    tif_files = list(ROOT_DIR.rglob("*.tif"))
    tif_files.extend(ROOT_DIR.rglob("*.tiff"))

    print(f"Found {len(tif_files)} TIFF files")

    for tif_file in tif_files:

        # Avoid reprocessing files already containing scale bars
        if tif_file.stem.endswith("_scalebar"):
            continue

        print()
        print("=" * 80)
        print(f"Processing: {tif_file}")

        try:
            add_scale_bar(tif_file)
        except Exception as e:
            print(f"FAILED: {tif_file}")
            print(e)

    print()
    print("Done.")


if __name__ == "__main__":
    main()