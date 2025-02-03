# Script used to draw where in the coordinate system the images are taken.
import numpy as np
import matplotlib.pyplot as plt
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
    metadata_dir = "C:\\Users\\honey\\OneDrive\\Desktop\\TreeRings\\code\\debugging\\metadata_ai.json"
    metadata = load_metadata(metadata_dir)
    coords = np.array(metadata["coordinates"])
    print(len(coords.flatten()))
    print(metadata["rows"] * metadata["cols"])
    reshaped = np.reshape(coords,(-1, 3))
    plot_coordinates(reshaped[:, 0], reshaped[:, 1], reshaped[:, 2])

if __name__ == "__main__":
    main()