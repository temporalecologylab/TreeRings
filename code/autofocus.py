import math
import argparse
import cv2
import time
from picamera2 import Picamera2

picam2 = Picamera2()
picam2.start()



def get_best_focus(start_mm, end_mm, step_size_mm, blur) -> float:
    best_focus_score = 0.0
    best_focus_position = 0.0

    steps = math.ceil((end_mm - start_mm)/step_size_mm) + 1

    for step in range (0, steps):
        position = start_mm + (step * step_size_mm)
        # move z-axis to pos?
        print("move z-axis up")
        time.sleep(5)
        image = picam2.capture_array()

        focus_score = calculate_focus_score(image, blur, position)
        if focus_score > best_focus_score:
            best_focus_score = focus_score
            best_focus_position = position
    
    return best_focus_position

def calculate_focus_score(image, blur, position) -> float:
    image_filtered = cv2.medianBlur(image, blur)
    laplacian = cv2.Laplacian(image_filtered,  cv2.CV_64F)
    focus_score = laplacian.var()
    print(focus_score)

    return focus_score



if __name__ == "__main__":
    # send in start_mm, end_mm, step_size_mm from calling script
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "start",
        action="store",
        type=float,
        # default= TODO: probs helpful to set a default once we have an intiton for that
    )
    parser.add_argument(
        "end",
        action="store",
        type=float,
        # default= TODO: probs helpful to set a default once we have an intiton for that
    )
    parser.add_argument(
        "step",
        action="store",
        type=float,
        # default= TODO: probs helpful to set a default once we have an intiton for that
    )
    parser.add_argument(
        "blur", #odd nums only
        action="store",
        type=float,
        # default= TODO: probs helpful to set a default once we have an intiton for that
    )

    best_focus =get_best_focus(0,10, 1, 1)

    print("best focus determined to be: ", format(best_focus))