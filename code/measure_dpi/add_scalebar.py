# Generated with ChatGPT-4.0

from pathlib import Path

import cv2
import numpy as np
import tifffile


PIXELS_PER_MM = 807.9
SCALE_BAR_MM = 10

MARGIN_PX = 150
BAR_WIDTH_PX = 40

# Text height relative to scale bar length
TEXT_HEIGHT_FRACTION = 0.08

# Gap between bar and text
TEXT_OFFSET_PX = 75


def add_scale_bar(input_file):

    input_file = Path(input_file)

    output_file = input_file.with_name(
        input_file.stem + "_scalebar" + input_file.suffix
    )

    print("Loading image...")
    img = tifffile.imread(input_file)

    print("Shape:", img.shape)
    print("Dtype:", img.dtype)

    if img.ndim != 3 or img.shape[2] < 3:
        raise ValueError(
            f"Expected RGB image, got shape {img.shape}"
        )

    height, width = img.shape[:2]

    bar_length_px = int(
        SCALE_BAR_MM * PIXELS_PER_MM
    )

    x0 = MARGIN_PX
    x1 = min(
        width,
        x0 + BAR_WIDTH_PX
    )

    y1 = height - MARGIN_PX
    y0 = max(
        0,
        y1 - bar_length_px
    )

    print("Drawing scale bar...")

    # Red vertical scale bar (RGB)
    img[y0:y1, x0:x1, 0] = 255
    img[y0:y1, x0:x1, 1] = 0
    img[y0:y1, x0:x1, 2] = 0

    print("Drawing label...")

    label = f"{SCALE_BAR_MM:g} mm"

    target_text_height_px = int(
        bar_length_px * TEXT_HEIGHT_FRACTION
    )

    (_, base_height), _ = cv2.getTextSize(
        label,
        cv2.FONT_HERSHEY_SIMPLEX,
        1.0,
        1,
    )

    font_scale = (
        target_text_height_px / base_height
    )

    font_thickness = max(
        2,
        int(target_text_height_px / 12)
    )

    (text_width, text_height), baseline = cv2.getTextSize(
        label,
        cv2.FONT_HERSHEY_SIMPLEX,
        font_scale,
        font_thickness,
    )

    text_x = x1 + TEXT_OFFSET_PX

    text_y = (
        y0
        + bar_length_px // 2
        + text_height // 2
    )

    # OpenCV uses BGR ordering for colors
    cv2.putText(
        img,
        label,
        (text_x, text_y),
        cv2.FONT_HERSHEY_SIMPLEX,
        font_scale,
        (255, 0, 0),
        font_thickness,
        cv2.LINE_AA,
    )

    print("Saving...")

    tifffile.imwrite(
        output_file,
        img,
        photometric="rgb",
        compression="lzw",
    )

    print(f"Saved: {output_file}")


if __name__ == "__main__":

    add_scale_bar(
        r"D:\\representative_scans\\core-scan-ts-he\\core-scan-ts-he.tif"
    )