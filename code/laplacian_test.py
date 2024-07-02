import cv2
import logging as log
import numpy as np
import queue
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from matplotlib import cm
from matplotlib import colors
import os

def focus_thread( img_pipeline, directory):
        while True:
            args = img_pipeline.get()
            log.info(args)
            i = args[0]
            j = args[1]
            z = args[2]
            if i == -1:
                img_pipeline.task_done()
                break
            for k in range (0, z):
                imgs = []
                imgs.append(cv2.imread("/{}/frame_{}_{}_{}.jpg".format(directory, i, j, k)))
                log.info("calling focus method")
                focused_image = best_focused_image(imgs)
                cv2.imwrite("/{}/focused_images/focused_{}_{}.jpg".format(directory,i,j), focused_image)
                img_pipeline.task_done()
        
def best_focused_image(images):
    best_image = []
    best_lap = 0.0

    for image in images:
        masked_image = hsl_mask(image)
        lap = compute_laplacian(masked_image)
        if lap.var() > best_lap:
            best_lap = lap.var()
            best_image = image

    return best_image

def hsl_mask(img):
    imgHSV = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)


    s_channel = imgHSV[:,:,1]
    mask = cv2.inRange(s_channel, 0, 150)
    # mask = cv2.inRange(imgHSV, np.array([0,250,0]), np.array([255,255,255]))
    res =np.dstack((imgRGB, mask))

    return res


def compute_laplacian(image):

    # odd numbers only, can be tuned
    kernel_size = 11         # Size of the laplacian window
    blur_size = 9           # How big of a kernel to use for the gaussian blur

    blurred = cv2.GaussianBlur(image, (blur_size,blur_size), 0)
    return cv2.Laplacian(blurred, cv2.CV_64F, ksize=kernel_size) 

if __name__ == "__main__":
    lap_map = {}
    dir = "test_images\\6"
    image_files = os.listdir(dir)
    print(image_files)
    focusimages = []

    for img in image_files:
        read_img = cv2.imread("{}\{}".format(dir, img))             
        focusimages.append(read_img)

    res = best_focused_image(focusimages)

    cv2.imwrite("{}/best.jpg".format(dir), res)