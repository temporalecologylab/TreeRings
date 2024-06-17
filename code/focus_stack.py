## Code inspired by https://github.com/cmcguinness/focusstack/tree/master

import numpy as np
import cv2
import os

def findHomography(image_1_kp, image_2_kp, matches):
    image_1_points = np.zeros((len(matches), 1, 2), dtype=np.float32)
    image_2_points = np.zeros((len(matches), 1, 2), dtype=np.float32)

    for i in range(0,len(matches)):
        image_1_points[i] = image_1_kp[matches[i].queryIdx].pt
        image_2_points[i] = image_2_kp[matches[i].trainIdx].pt


    homography, mask = cv2.findHomography(image_1_points, image_2_points, cv2.RANSAC, ransacReprojThreshold=2.0)

    return homography



def align_images(images):

    # TODO: SIFT not open source? im not sure this is still true (cmcguinness code hasnt been updated in 8 yrs and SIFT now fully integrated into OpenCV, but maybe worth looking futher into before publishing)

    use_sift = True

    outimages = []

    if use_sift:
        detector = cv2.SIFT_create()
    else:
        detector = cv2.ORB_create(1000)

    #   We assume that image 0 is the "base" image and align everything to it
    outimages.append(images[0])
    image1gray = cv2.cvtColor(images[0],cv2.COLOR_BGR2GRAY)
    image_1_kp, image_1_desc = detector.detectAndCompute(image1gray, None)

    print(images)
    for i in range(1,len(images)):
        print("Aligning image {}".format(i))
        image_i_kp, image_i_desc = detector.detectAndCompute(images[i], None)

        if use_sift:
            bf = cv2.BFMatcher()
            # This returns the top two matches for each feature point (list of list)
            pairMatches = bf.knnMatch(image_i_desc,image_1_desc, k=2)
            rawMatches = []
            for m,n in pairMatches:
                if m.distance < 0.7*n.distance:
                    rawMatches.append(m)
        else:
            bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
            rawMatches = bf.match(image_i_desc, image_1_desc)

        sortMatches = sorted(rawMatches, key=lambda x: x.distance)
        matches = sortMatches[0:128]



        hom = findHomography(image_i_kp, image_1_kp, matches)
        newimage = cv2.warpPerspective(images[i], hom, (images[i].shape[1], images[i].shape[0]), flags=cv2.INTER_LINEAR)

        outimages.append(newimage)
        # If you find that there's a large amount of ghosting, it may be because one or more of the input
        # images gets misaligned.  Outputting the aligned images may help diagnose that.
        cv2.imwrite("aligned{}.png".format(i), newimage)

    return outimages

#
#   Compute the gradient map of the image
def compute_laplacian(image):

    # YOU SHOULD TUNE THESE VALUES TO SUIT YOUR NEEDS
    kernel_size = 5         # Size of the laplacian window
    blur_size = 5           # How big of a kernal to use for the gaussian blur
                            # Generally, keeping these two values the same or very close works well
                            # Also, odd numbers, please...

    blurred = cv2.GaussianBlur(image, (blur_size,blur_size), 0)
    return cv2.Laplacian(blurred, cv2.CV_64F, ksize=kernel_size)

def crop(image):
    print(image[0:5])
    y_nonzero, x_nonzero, _ = np.nonzero(image)
    return image[np.min(y_nonzero):np.max(y_nonzero), np.min(x_nonzero):np.max(x_nonzero)]

def focus_stack(unimages):
    images = align_images(unimages)

    print("Computing the laplacian of the blurred images")
    laps = []
    for i in range(len(images)):
        laps.append(compute_laplacian(cv2.cvtColor(images[i],cv2.COLOR_BGR2GRAY)))

    laps = np.asarray(laps)
    print("Shape of array of laplacians = {}".format(laps.shape))

    output = np.zeros(shape=images[0].shape, dtype=images[0].dtype)

    abs_laps = np.absolute(laps)
    maxima = abs_laps.max(axis=0)
    bool_mask = abs_laps == maxima
    mask = bool_mask.astype(np.uint8)
    for i in range(0,len(images)):
        output = cv2.bitwise_not(images[i],output, mask=mask[i])

    output = crop(output)	
    
    return 255-output

def crop_stacked(img_stacked):
    combined = img_stacked[:, :, 0] + img_stacked[:, :, 1] + img_stacked[:, :, 2]
    black_idx = np.where(combined == 0)

    rows = black_idx[0]
    cols = black_idx[1]
    # upper left corner is origin, therefore max row and max col are bottom right

    min_row = min(rows)
    max_row = max(rows)
    min_col = min(cols)
    max_col = max(cols)

    # top left -> (min_row, min_col)
    tl = (min_row, min_col)
    # top right -> (min_row, max_col)
    tr = (min_row, max_col)
    # bottom left ->(max_row, min_col)
    bl = (max_row, min_col)
    # bottom right -> (max_row, max_col)
    br = (max_row, max_col)

    # row_tr = 
    # col_tr = 

    # row_br = 
    # col_br = 

    # row_bl = 
    # col_bl = 

    print("test")

if __name__ == "__main__":
    # image_files = os.listdir("edge_imgs")
    # focusimages = []
    # for img in image_files:
    #     focusimages.append(cv2.imread("edge_imgs/{}".format(img)))

    # img = focus_stack (focusimages)


    # cv2.imwrite("stackedimg.jpg", img)

    os.chdir("c:/code/TreeRings/code")
    print(os.getcwd())
    img = cv2.imread("stackedimg.jpg")
    crop_stacked(img)

    cv2.imwrite("og.jpg", img)
    cv2.imwrite("new.jpg", img[img.nonzero()])
    cv2.waitKey(0)
