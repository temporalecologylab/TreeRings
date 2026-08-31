# Generated with ChatGPT-4.0
from pathlib import Path

import cv2
import numpy as np
import tifffile


PIXELS_PER_MM = 807.9
SCALE_BAR_MM = 50

START_X = 1086
START_Y = 3558

BAR_HEIGHT_PX = 40

TEXT_HEIGHT_FRACTION = 0.01
TEXT_OFFSET_PX = 100


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

    bar_length_px = int(
        SCALE_BAR_MM * PIXELS_PER_MM
    )

    x0 = START_X
    x1 = START_X + bar_length_px

    y0 = START_Y
    y1 = START_Y + BAR_HEIGHT_PX

    print("Drawing scale bar...")

    # Red horizontal scale bar
    img[y0:y1, x0:x1, 0] = 255
    img[y0:y1, x0:x1, 1] = 0
    img[y0:y1, x0:x1, 2] = 0

    print("Drawing label...")

    label = f"{SCALE_BAR_MM:g} mm"

    target_text_height_px = int(
        BAR_HEIGHT_PX + bar_length_px * TEXT_HEIGHT_FRACTION
    )

    (_, base_height), _ = cv2.getTextSize(
        label,
        cv2.FONT_HERSHEY_SIMPLEX,
        1.0,
        1,
    )

    font_scale = target_text_height_px / base_height

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

    # Center text over bar
    text_x = x0 + (bar_length_px - text_width) // 2

    text_y = y0 - TEXT_OFFSET_PX

    img = cv2.putText(
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
        r"D:\\representative_scans\\caliper\\caliper.tif"
    )