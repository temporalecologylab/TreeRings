import math
import argparse
import cv2
import time
from picamera2 import Picamera2

picam2 = Picamera2()
picam2.start()

class Autofocus:

    def __init__(self):
        pass

    ## recursive function to find the best focus across a large z-axis distance
    ## to initialize, choose a deceptively large distance between start and end, 0 for best_focus_score and best_focus_position
    ## the function will find the best Laplacian focus score for the range chosen, then "zoom in" by recursing over the smaller region encompassing the current best focus score until there is no more improvement

    def get_best_focus(self, start_mm, end_mm, best_focus_score, best_focus_position, blur) -> tuple[float, float]:
        current_best_focus_score = 0.0
        current_best_focus_position = 0.0

        step_size_mm = start_mm + end_mm / 5

        steps = math.ceil((end_mm - start_mm)/step_size_mm) + 1

        for step in range (0, steps):
            position = start_mm + (step * step_size_mm)
            # move z-axis to pos?
            print("move z-axis up")
            time.sleep(5)
            image = picam2.capture_array()

            focus_score = self.calculate_focus_score(image, blur)
            if focus_score > current_best_focus_score:
                current_best_focus_score = focus_score
                current_best_focus_position = position
        if current_best_focus_score > best_focus_score:
            return self.get_best_focus(current_best_focus_position-step_size_mm, current_best_focus_position+step_size_mm, current_best_focus_position, current_best_focus_score)
        else:
            return (best_focus_score, best_focus_position)
        
    ## calculates focus score using 
    def calculate_focus_score(image, blur) -> float:
        image_filtered = cv2.medianBlur(image, blur)
        laplacian = cv2.Laplacian(image_filtered,  cv2.CV_64F)
        focus_score = laplacian.var()
        print(focus_score)

        return focus_score



# if __name__ == "__main__":
#     # send in start_mm, end_mm, step_size_mm from calling script
#     parser = argparse.ArgumentParser()
#     parser.add_argument(
#         "start",
#         action="store",
#         type=float,
#         # default= TODO: probs helpful to set a default once we have an intiton for that
#     )
#     parser.add_argument(
#         "end",
#         action="store",
#         type=float,
#         # default= TODO: probs helpful to set a default once we have an intiton for that
#     )
#     parser.add_argument(
#         "step",
#         action="store",
#         type=float,
#         # default= TODO: probs helpful to set a default once we have an intiton for that
#     )
#     parser.add_argument(
#         "blur", #odd nums only
#         action="store",
#         type=float,
#         # default= TODO: probs helpful to set a default once we have an intiton for that
#     )

#     args = parser.parse_args()
    
#     best_focus = get_best_focus(args.start, args.end, args.step, args.blur)
#     best_focus = get_best_focus(0,10, 1, 1)

#     print("best focus determined to be: ", best_focus)