import matplotlib.pyplot as plt
import cv2
import math
import imutils

# --- EDIT HERE --- 
IMAGE = cv2.imread("./test_dpi.tiff") # image which contains a known distance. Preferably a slide ruler.
RESIZE_PERCENTAGE = 0.3 # percentage to resize the image. Needs to match what downscale applied to the samples. Check the scan metadata.json file if you are unsure.
DISTANCE_MM = 0.5 # known distance that you will click in the image in millimeters
# --- END EDIT HERE ---

# If False, it will show the full resolution, if True it will show the resized
IMAGE_RESIZED = imutils.resize(IMAGE, width = int(IMAGE.shape[1] * RESIZE_PERCENTAGE)) 
SHOW_RESIZED = True

# Variables to store the two points and their confirmation states
point1 = None
point2 = None
confirmed_point1 = False
confirmed_point2 = False

# Variables to store the dot objects for point1 and point2
dot1 = None
dot2 = None

def on_click(event):
    """Callback function for mouse click events."""
    global point1, point2, confirmed_point1, confirmed_point2, dot1, dot2

    # Check if the click is within the plot area
    if event.inaxes:
        # Left mouse button: Select or overwrite points
        if event.button == 1:  # Left button
            if not confirmed_point1:
                # Update point1
                point1 = (event.xdata, event.ydata)
                print(f"Point 1 selected: {point1}")

                # Update the dot for point1
                if dot1:
                    dot1.remove()  # Remove the previous dot
                dot1, = event.inaxes.plot(point1[0], point1[1], 'bo')  # Blue dot for point1
                plt.draw()  # Redraw the plot
            elif confirmed_point1 and not confirmed_point2:
                # Update point2
                point2 = (event.xdata, event.ydata)
                print(f"Point 2 selected: {point2}")

                # Update the dot for point2
                if dot2:
                    dot2.remove()  # Remove the previous dot
                dot2, = event.inaxes.plot(point2[0], point2[1], 'go')  # Green dot for point2
                plt.draw()  # Redraw the plot

        # Right mouse button: Confirm points
        elif event.button == 3:  # Right button
            if point1 and not confirmed_point1:
                # Confirm point1
                confirmed_point1 = True
                print(f"Point 1 confirmed: {point1}")
            elif point2 and confirmed_point1 and not confirmed_point2:
                # Confirm point2
                confirmed_point2 = True
                print(f"Point 2 confirmed: {point2}")

                # Draw the line once both points are confirmed
                ax = event.inaxes
                x_values = [point1[0], point2[0]]
                y_values = [point1[1], point2[1]]
                ax.plot(x_values, y_values, 'r-', label="Selected Line")
                plt.draw()  # Update the plot

                dpi = calculate_dpi(point1, point2, DISTANCE_MM)
                # Reset state for the next line
                reset_points()


def reset_points():
    """Reset global variables for selecting a new line."""
    global point1, point2, confirmed_point1, confirmed_point2
    point1 = None
    point2 = None
    confirmed_point1 = False
    confirmed_point2 = False
    dot1 = None
    dot2 = None

def calculate_dpi(pt1, pt2, dist_mm):
    """Calculates DPI from the distance between the two clicked points and the known distance between them"""
    hyp = math.sqrt(abs((pt1[0] - pt2[0])**2 + (pt1[1] - pt2[1])**2))# hypotenuse with pythagorean theorem

    mm_to_in = 25.4 
    dpi = (hyp / dist_mm) * mm_to_in

    print("DPI is: {}".format(dpi))
    print("Line Length: {}".format(hyp))
    print("Entered Distance: {}".format(DISTANCE_MM))

    return dpi

# Create a figure and axis
fig, ax = plt.subplots()
ax.set_title("Left click to select points, right click to confirm")

if SHOW_RESIZED:
    ax.imshow(IMAGE_RESIZED)
else:
    ax.imshow(IMAGE)

# Connect the click event to the callback
fig.canvas.mpl_connect('button_press_event', on_click)

# Show the plot
plt.show()
