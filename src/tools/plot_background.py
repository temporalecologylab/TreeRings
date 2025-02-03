# Script used to draw where in the coordinate system the images are taken.
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sn 

import json

def load_metadata(metadata_dir):
    
    with open(metadata_dir) as f:
        metadata = json.load(f)
        f.close()

    return metadata

def main():
    metadata_dir = "C:\\Users\\honey\\OneDrive\\Desktop\\TreeRings\\code\\debugging\\metadata_ai.json"
    metadata = load_metadata(metadata_dir)
    background = np.array(metadata["background"])
    background_std = np.array(metadata["background_std"])
    
    hm = sn.heatmap(data=background)
    plt.show()
    hm_std = sn.heatmap(data = background_std, annot=True)
    plt.show()

    


if __name__ == "__main__":
    main()