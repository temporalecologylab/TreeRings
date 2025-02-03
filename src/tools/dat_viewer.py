import numpy as np
import json
import matplotlib.pyplot as plt
import cv2

def load_metadata(metadata_dir):
    
    with open(metadata_dir) as f:
        metadata = json.load(f)
        f.close()

    return metadata

def main():
    directory = "C:\\Users\\honey\\OneDrive\\Desktop\\TreeRings\\code\\debugging"

    metadata = load_metadata(directory + "\\metadata.json")
    memmap_array = np.memmap(directory + "\\mosaic_90per.dat", dtype='uint8', mode='r', shape=(metadata["pixels_h"], metadata["pixels_w"], metadata["depth"]))

    cv2.rotate(memmap_array, cv2.ROTATE_90_CLOCKWISE)

    tl = (0, int(metadata["pixels_w"] / 2) + 600)
    fov_h = metadata["pixels_h"]
    fov_w = 800

    plt.imshow(memmap_array[tl[0]:tl[0]+fov_h, tl[1]:tl[1]+fov_w, :])
    plt.show()

if __name__ == "__main__":
    main()