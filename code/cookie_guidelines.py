import matplotlib.pyplot as plt
import numpy as np
import tkinter as tk
from tkinter import filedialog
import os
import tifffile
import math
import utils
import cv2

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

def click_pit(tiff_path):
    """
    Wait for the user to click on the pit in the image using matplotlib.
    Args:
        tiff_path (str): Path of the image to load.
    Returns:
        tuple: (x, y) coordinates of the clicked pit.
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

    ax.imshow(image)
    ax.set_title("Left click the pit, Right click to progress")
    plt.axis("off")
    cid = fig.canvas.mpl_connect('button_press_event', on_click)
    plt.show(block=True)
    
def write_guidelines(image_path, metadata_path, center, endpoint0, endpoint1, endpoint2, one_directory = False):
    metadata = utils.load_metadata(metadata_path)
    image = tifffile.imread(image_path)
    thickness = 1
    r = (255, 0, 0)
    g = (0, 255, 0)
    b = (0, 0, 255)
    image = cv2.line(image, center, endpoint0, r, thickness) 
    image = cv2.line(image, center, endpoint1, g, thickness) 
    image = cv2.line(image, center, endpoint2, b, thickness) 

    if one_directory:
        i = 1
        if not os.path.exists("./cookies_with_guides"):
            os.makedirs("./cookies_with_guides")
            
        final_path = os.path.join("./cookies_with_guides", "{}_{}_{}_guides.tif".format(metadata["species"], metadata['id1'], metadata["id2"]))
        while os.path.exists(final_path):
            final_path = os.path.join(os.path.dirname(final_path), "{}_{}_{}_guides_{}.tif".format(metadata["species"], metadata['id1'], metadata["id2"], i))
            i+=1
    else:
        final_path = os.path.join(os.path.dirname(image_path), "{}_{}_{}_guides.tif".format(metadata["species"], metadata['id1'], metadata["id2"]))

    tifffile.imwrite(
                final_path,
                image,
                photometric='rgb',
                compression='LZW'
    )
    print("Guidelines saved at {}".format(final_path))

def reset():
    global confirmed_pit, pit, dot, line, points, finished
    confirmed_pit = False
    pit = None
    dot = None
    line = None
    points = []
    finished = False

def main():
    parent_dir = prompt_directory()
    if not parent_dir:
        print("No directory selected. Exiting.")
        return

    tiff_files = []
    metadata_files = []
    for root, dirs, files in os.walk(parent_dir):
        for filename in files:
            if '.tif' in filename:
                tiff_files.append(os.path.join(root, filename))
                metadata_files.append(os.path.join(root, 'metadata.json'))

    for tiff_file, metadata_file in zip(tiff_files, metadata_files):

        click_pit(tiff_file)
        if len(points) == 4:
            write_guidelines(tiff_file, metadata_file, points[0], points[1], points[2], points[3], ONE_DIR)
        reset()

    print("Pit confirmation complete. Proceeding to the next steps...")


if __name__ == "__main__":
    main()
