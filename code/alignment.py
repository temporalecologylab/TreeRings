# adapted from https://pyimagesearch.com/2015/09/07/blur-detection-with-opencv/
from imutils import paths
import argparse
import numpy as np
import cv2
import os
import time
import logging as log
import camera

import utils

log.basicConfig(format='%(process)d-%(levelname)s-%(message)s', level=log.INFO)


class Alignment: 
    
    def __init__(self):
        self.config = utils.load_config 
        
    def variance_of_laplacian(image):
        """Compute the Laplacian of the image and return the focus measure."""
        return cv2.Laplacian(image, cv2.CV_64F).var()

    def center_band_grid(image, n_col, band_height_frac=0.2):
        """
        Create tiles that intersect the horizontal midpoint of the image.
        Each tile spans a portion of the width (n_col divisions)
        and covers a horizontal band centered vertically.
        """
        h, w = image.shape[:2]
        band_half = int((h * band_height_frac) / 2)
        cy = h // 2

        y_start = max(cy - band_half, 0)
        y_end   = min(cy + band_half, h)

        x_breaks = np.linspace(0, w, n_col + 1, dtype=int)
        tiles = []
        for c in range(n_col):
            x0, x1 = x_breaks[c], x_breaks[c+1]
            tile = image[y_start:y_end, x0:x1]
            tiles.append(tile)

        return tiles, (y_start, y_end), x_breaks
        

# -------------------------------------------------------

ap = argparse.ArgumentParser()
ap.add_argument("-i", "--images", required=True,
    help="path to input directory of images")
ap.add_argument("-t", "--threshold", type=float, default=200.0,
    help="focus measures that fall below this value will be considered 'blurry'")
ap.add_argument("-c", "--ncol", type=int, default=4,
    help="number of grids across the width of the image")
ap.add_argument("-b", "--bandheight", type=float, default=0.2,
    help="fraction of image height for the horizontal band (0.0–1.0)")
ap.add_argument("-s", "--show", action="store_true",
    help="show annotated images in a window (optional)")
args = vars(ap.parse_args())

# -------------------------------------------------------


if __name__ == "__main__":
    
    
    input_dir = os.path.abspath(args["images"])
    output_dir = input_dir + "_score"
    os.makedirs(output_dir, exist_ok=True)
    print(f"[INFO] Saving scored images to: {output_dir}")

    for imagePath in paths.list_images(args["images"]):
        filename = os.path.basename(imagePath)
        save_path = os.path.join(output_dir, filename)

        original = cv2.imread(imagePath)
        if original is None:
            print(f"[WARNING] Could not read {imagePath}")
            continue

        image = original.copy()
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        t0 = time.time()

        # Create band grid
        tiles, (y_start, y_end), x_breaks = center_band_grid(
            gray, args["ncol"], band_height_frac=args["bandheight"]
        )

        for c, tile in enumerate(tiles):
            fm = variance_of_laplacian(tile)
            label = f"{fm:.1f}"
            color = (0, 0, 255) if fm < args["threshold"] else (255, 0, 0)

            # Tile geometry
            x0, x1 = x_breaks[c], x_breaks[c+1]
            tile_w = x1 - x0
            tile_h = y_end - y_start

            # Center label in tile
            text_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 1.5, 3)
            text_w, text_h = text_size
            x_text = x0 + (tile_w - text_w) // 2
            y_text = y_start + (tile_h + text_h) // 2

            cv2.putText(image, label, (x_text, y_text),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)

        # Draw grid lines
        for xb in x_breaks:
            cv2.line(image, (xb, y_start), (xb, y_end), (200, 200, 200), 2)
        cv2.line(image, (0, y_start), (image.shape[1], y_start), (200, 200, 200), 2)
        cv2.line(image, (0, y_end), (image.shape[1], y_end), (200, 200, 200), 2)

        t1 = time.time()
        print(f"[INFO] Processed {filename} in {(t1 - t0):.3f}s")

        cv2.imwrite(save_path, image)

        if args["show"]:
            cv2.namedWindow("Scored Image", cv2.WINDOW_NORMAL)
            cv2.imshow("Scored Image", image)
            key = cv2.waitKey(0)
            if key == 27:
                break

    cv2.destroyAllWindows()
    print("[INFO] Done.")
