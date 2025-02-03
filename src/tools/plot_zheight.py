# Script used to draw where in the coordinate system the images are taken.
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sn 
import pandas as pd
import json

def load_metadata(metadata_dir):
    
    with open(metadata_dir) as f:
        metadata = json.load(f)
        f.close()

    return metadata

def plot_coordinates(x, y, z):
    ax = plt.figure().add_subplot(projection='3d')
    ax.plot(x, y, z, label='parametric curve')
    ax.legend()
    plt.show()
    return
    
def main():
    metadata_dir = "C:\\Users\\honey\\OneDrive\\Desktop\\TreeRings\\code\\debugging\\metadata_bigcookie.json"
    metadata = load_metadata(metadata_dir)
    coords = np.array(metadata["coordinates"])
    rows = np.array(metadata["rows"])
    cols = np.array(metadata["cols"])
    reshaped = coords.reshape((rows, cols, 3))
    z_vals = reshaped[:, :, 2]
    diff = np.diff(z_vals)    
    
    ## Add values inside each cell
    # hm = sn.heatmap(data=z_vals, annot=True)

    # Don't add values for big matrices
    hm = sn.heatmap(data=diff)
    plt.show()


if __name__ == "__main__":
    main()