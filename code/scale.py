import cv2
import numpy as np

def overlay_scale_bar(image, pixel_size, scale_bar_length_mm=2, bar_height=50, bar_color=(255, 255, 0), text_color=(255, 255, 0), font_scale=3.5, thickness=10):
    """
    Overlays a scale bar on the given image using OpenCV.

    Parameters:
    - image: OpenCV image array (numpy array).
    - pixel_size: Physical size of one pixel in mm.
    - scale_bar_length_mm: Length of the scale bar in millimeters.
    - bar_height: Height of the scale bar in pixels.
    - bar_color: Color of the scale bar in BGR.
    - text_color: Color of the text on the scale bar in BGR.`
    - font_scale: Scale of the font for the numbers.
    - thickness: Thickness of the scale bar and text.

    Returns:
    - Image with the scale bar overlay.
    """

    # Convert scale bar length to pixels
    scale_bar_length_px = int(scale_bar_length_mm / pixel_size)

    # Bottom-left corner of the scale bar
    margin = 100  # Margin from the edge
    x_start = margin
    y_start = image.shape[0] - bar_height - margin

    # Draw the main scale bar
    cv2.rectangle(image, (x_start, y_start), (x_start + scale_bar_length_px, y_start + bar_height), bar_color, -1)
    #cv2.rectangle(image, (100, 100), (500, 120), (255, 255, 0), -1)

    # Draw graduations and labels
    for i in range(1, scale_bar_length_mm + 1):
        x_pos = x_start + int(i / pixel_size)
        # Larger graduation for 5 mm increments
        if i % 5 == 0:
            cv2.line(image, (x_pos, y_start), (x_pos, y_start - bar_height), bar_color, thickness)
            text = f"{i}"
            text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)[0]
            text_x = x_pos - text_size[0] // 2
            text_y = y_start - bar_height - text_size[1] - 2
            cv2.putText(image, text, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, font_scale, text_color, thickness)
        else:
            # Smaller graduation for other increments
            cv2.line(image, (x_pos, y_start), (x_pos, y_start - bar_height // 2), bar_color, thickness)


    return image

# Example usage:

def main():
    img = cv2.imread("c:\\Users\\honey\\Downloads\\BETPOP_WM8_P16\\10per\\mosaic_10per.tif")
    
    DPI = 1648.26
    
    pixel_size_mm = 25.4 / DPI  # Example pixel size in mm

    bar_height = int(img.shape[0] * 0.02)
    thickness = int(bar_height / 5 )
    font_scale = int(thickness / 5)
    img_with_scale_bar = overlay_scale_bar(img, pixel_size_mm, scale_bar_length_mm=25, bar_height = bar_height, font_scale =  font_scale, thickness=thickness)

    cv2.namedWindow("Image with Scale Bar", cv2.WINDOW_NORMAL)
    cv2.imshow('Image with Scale Bar', img_with_scale_bar)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    

if __name__ == "__main__":
    main()