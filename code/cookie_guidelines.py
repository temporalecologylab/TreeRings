import matplotlib.pyplot as plt
import tkinter as tk
from tkinter import filedialog
import os
import tifffile
import math
import utils
import cv2
import json

ONE_DIR = True
confirmed_pit = False
pit = None
dot = None
line = None
finished = False
points = []

def prompt_directory():
    """
    Prompt the user to select a parent directory containing the cookie images.
    Returns:
        str: Path to the selected directory.
    """
    root = tk.Tk()
    root.withdraw()  # Hide the main tkinter window
    directory = filedialog.askdirectory(title="Select Parent Directory")
    return directory

def click_pit(tiff_path: str):
    """
    Allows user to click the center of a pit in an image using the standard Matplotlib image viewer. Left click selects a pit. Right click confirms the selection. 
    Right click again to close the window.

    Args:
        tiff_path (str): Path of the image to load.
    Returns:
        None
    """
    coords = []

    fig, ax = plt.subplots()
    # Display a preview of the TIFF image
    image = tifffile.imread(tiff_path)

    def on_click(event):
        """Callback function for mouse click events."""
        global pit, confirmed_pit, dot, line, points, finished

        # Check if the click is within the plot area
        if event.inaxes:
            # Left mouse button: Select or overwrite points
            if event.button == 1:  # Left button
                if not finished:
                    # Update pit
                    pit = (int(event.xdata), int(event.ydata))
                    print(f"Pit selected: {pit}")

                    # Update the dot for pit
                    if dot:
                        dot.remove()  # Remove the previous dot
                    dot, = event.inaxes.plot(pit[0], pit[1], 'bo')  # Blue dot for pit
                    plt.draw()  # Redraw the plot
        
            # Right mouse button: Confirm point and plot guidelines
            elif event.button == 3:  # Right button
                if pit and not finished:
                        # Calulate theta = 0 line
                        dot.remove()
                        
                        x0 = pit[0]
                        y0 = pit[1]

                        x1 = image.shape[1]
                        y1 = pit[1]

                        points.append([x0, y0])
                        points.append([x1, y1])
                        
                        x_values_0 = [x0, x1]
                        y_values_0 = [y0, y1]


                        # Calculate theta = 120 degrees line
                        # y = mx + b 
                        m = math.atan(60) #60 degrees in radians, positive slope
                        b = y0 - m * x0 # b = y0 - m*x0

                        # does the second point intersect the top boundary of the image or the left boundary
                        # x = (y - b)/m 
                        y2_pot = 0
                        x2_pot = (y2_pot - b) / m

                        if x2_pot > 0:
                            x2 = int(x2_pot)
                            y2 = 0
                        else:
                            x2 = 0
                            y2 = int(b)

                        points.append([x2, y2])
                        x_values_1 = [x0, x2]
                        y_values_1 = [y0, y2]

                        # Calculate theta = 240 degrees line
                        # y = mx + b 
                        m = -math.atan(60) # -60 degrees in radians, positive slope
                        b = y0 - m * x0 # b = y0 - m*x0

                        # does the second point intersect the bottom boundary of the image or the left boundary
                        # x = (y - b)/m  
                        y3_pot = image.shape[0]
                        x3_pot = (y3_pot - b) / m

                        if x3_pot > 0:
                            x3 = int(x3_pot)
                            y3 = image.shape[0]
                        else:
                            x3 = 0
                            y3 = int(b)

                        points.append([x3, y3])
                        x_values_2 = [x0, x3]
                        y_values_2 = [y0, y3]

                        line, = event.inaxes.plot(x_values_0, y_values_0, 'r-')
                        line, = event.inaxes.plot(x_values_1, y_values_1, 'g-')
                        line, = event.inaxes.plot(x_values_2, y_values_2, 'b-')

                        finished = True
                        plt.draw()
                else: 
                    plt.close()
    ax.imshow(image)
    ax.set_title("Left click the pit, Right click to progress")
    plt.axis("off")
    cid = fig.canvas.mpl_connect('button_press_event', on_click)
    plt.show(block=True)
    
def write_guidelines(image_path:str , metadata_path:str, center:list[int], endpoint0:list[int], endpoint1:list[int], endpoint2:list[int], parent_dir, one_directory:bool = False):
    """Use the guidelines generated from the user clicks to draw on the original image and save the result. Default is to save the new image in the source directory of the image but
    this can also be saved to one general directory using the one_directory = True.

    Args:
        image_path (str): Path to source tiff image.
        metadata_path (str): Path to source metadata for the tiff image.
        center (list[int]): Coordinates of the pit.
        endpoint0 (list[int]): Coordinates of the first endpoint, with an angle of theta = 0 degrees.
        endpoint1 (list[int]): Coordinates of the second endpoint, with an angle of theta = 120 degrees.
        endpoint2 (list[int]): Coordinates of the third endpoint, with an angle of theta = 240 degrees.
        one_directory (bool, optional): Set as False if the image with a guideline wants to be saved in the original path. If True, all images will be saved in the working directory under './cookies_with_guidelines'. In this case, metadata is also copied with an associated filename. Defaults to False.
    """

    # Load data 
    # metadata = utils.load_metadata(metadata_path)
    f = open(metadata_path)
    metadata = json.load(f)
    f.close()

    image = tifffile.imread(image_path)

    # Set line parameters
    thickness = 1
    r = (255, 0, 0)
    g = (0, 255, 0)
    b = (0, 0, 255)

    # Draw lines
    image = cv2.line(image, center, endpoint0, r, thickness) 
    image = cv2.line(image, center, endpoint1, g, thickness) 
    image = cv2.line(image, center, endpoint2, b, thickness) 

    # Save in one directory 
    if one_directory:
        i = 1

        # Create the directory
        if not os.path.exists("{}/cookies_with_guides".format(parent_dir)):
            os.makedirs("{}/cookies_with_guides".format(parent_dir))

        # It's possible for multiple samples of the same plot to exist... must append values to their names if they already exist to not overwrite
        image_path_final = os.path.join("{}/cookies_with_guides".format(parent_dir), "{}_{}_{}_guides.tif".format(metadata["species"], metadata['id1'], metadata["id2"]))
        metadata_path_final =  os.path.join("{}/cookies_with_guides".format(parent_dir), "{}_{}_{}_metadata.json".format(metadata["species"], metadata['id1'], metadata["id2"]))
        while os.path.exists(image_path_final):
            image_path_final = os.path.join(os.path.dirname(image_path_final), "{}_{}_{}_guides_{}.tif".format(metadata["species"], metadata['id1'], metadata["id2"], i))
            metadata_path_final =  os.path.join(os.path.dirname(image_path_final), "{}_{}_{}_metadata_{}.json".format(metadata["species"], metadata['id1'], metadata["id2"], i))
            i+=1

        # write metadata if saving to the new folder
        # utils.write_metadata(metadata, metadata_path_final)
        with open(metadata_path_final, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=4)
    # Save in source directory. No need to write metadata again if in source directory
    else:
        image_path_final = os.path.join(os.path.dirname(image_path), "{}_{}_{}_guides.tif".format(metadata["species"], metadata['id1'], metadata["id2"]))
        metadata_path_final =  os.path.join(os.path.dirname(image_path), "{}_{}_{}_metadata.json".format(metadata["species"], metadata['id1'], metadata["id2"]))

    # Write file
    tifffile.imwrite(
                image_path_final,
                image,
                photometric='rgb',
                compression='LZW'
    )
    print("Guidelines saved at {}".format(image_path_final))

def reset():
    """Resets the global variables that are accessed by the event based 'on_click' callback.
    """
    global confirmed_pit, pit, dot, line, points, finished
    confirmed_pit = False
    pit = None
    dot = None
    line = None
    points = []
    finished = False

def main():
    # Get directory
    parent_dir = prompt_directory()
    if not parent_dir:
        print("No directory selected. Exiting.")
        return

    # Data stubs
    tiff_files = []
    metadata_files = []

    # Walk the parent directory and find all tif files. Make sure to get the metadata as well
    for root, _, files in os.walk(parent_dir):
        for filename in files:
            if '.tif' in filename and '._' not in filename:
                tiff_files.append(os.path.join(root, filename))
                metadata_files.append(os.path.join(root, 'metadata.json'))

    # Iterate through all of the tiff files found
    for tiff_file, metadata_file in zip(tiff_files, metadata_files):
        click_pit(tiff_file)

        if len(points) == 4:
            write_guidelines(tiff_file, metadata_file, points[0], points[1], points[2], points[3], parent_dir, ONE_DIR)
        reset()

    print("Pit confirmation complete. Proceeding to the next steps...")


if __name__ == "__main__":
    main()
