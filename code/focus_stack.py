## Code inspired by https://github.com/cmcguinness/focusstack/tree/master

import numpy as np
import cv2
import os
import logging as log

log.basicConfig(format='%(process)d-%(levelname)s-%(message)s', level=log.INFO)

class FocusStack:

    def __init__(self):
        pass

    def findHomography(self, image_1_kp, image_2_kp, matches):
        image_1_points = np.zeros((len(matches), 1, 2), dtype=np.float32)
        image_2_points = np.zeros((len(matches), 1, 2), dtype=np.float32)

        for i in range(0,len(matches)):
            image_1_points[i] = image_1_kp[matches[i].queryIdx].pt
            image_2_points[i] = image_2_kp[matches[i].trainIdx].pt


        homography, mask = cv2.findHomography(image_1_points, image_2_points, cv2.RANSAC, ransacReprojThreshold=2.0)

        return homography



    def align_images(self, images):

        # TODO: SIFT not open source? im not sure this is still true (cmcguinness code hasnt been updated in 8 yrs and SIFT now fully integrated into OpenCV, but maybe worth looking futher into before publishing)

        use_sift = True

        outimages = []

        if use_sift:
            log.info("using sift")
            detector = cv2.SIFT_create()
        else:
            detector = cv2.ORB_create(1000)

        #   We assume that image 0 is the "base" image and align everything to it
        outimages.append(images[0])
        image1gray = cv2.cvtColor(images[0],cv2.COLOR_BGR2GRAY)
        image_1_kp, image_1_desc = detector.detectAndCompute(image1gray, None)

        log.info("begin alignment")
        for i in range(1,len(images)):
            log.info("Aligning image {}".format(i))
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



            hom = self.findHomography(image_i_kp, image_1_kp, matches)
            newimage = cv2.warpPerspective(images[i], hom, (images[i].shape[1], images[i].shape[0]), flags=cv2.INTER_LINEAR)

            outimages.append(newimage)
            # If you find that there's a large amount of ghosting, it may be because one or more of the input
            # images gets misaligned.  Outputting the aligned images may help diagnose that.
            cv2.imwrite("aligned{}.png".format(i), newimage)

        return outimages

    #
    #   Compute the gradient map of the image
    def compute_laplacian(self,image):

        # YOU SHOULD TUNE THESE VALUES TO SUIT YOUR NEEDS
        kernel_size = 5         # Size of the laplacian window
        blur_size = 5           # How big of a kernal to use for the gaussian blur
                                # Generally, keeping these two values the same or very close works well
                                # Also, odd numbers, please...

        blurred = cv2.GaussianBlur(image, (blur_size,blur_size), 0)
        return cv2.Laplacian(blurred, cv2.CV_64F, ksize=kernel_size)

    def focus_stack(self, unimages):

        log.info("focus stack begin")
        images = self.align_images(unimages)

        log.info("Computing the laplacian of the blurred images")
        laps = []
        for i in range(len(images)):
            laps.append(self.compute_laplacian(cv2.cvtColor(images[i],cv2.COLOR_BGR2GRAY)))

        laps = np.asarray(laps)
        log.info("Shape of array of laplacians = {}".format(laps.shape))

        output = np.zeros(shape=images[0].shape, dtype=images[0].dtype)

        abs_laps = np.absolute(laps)
        maxima = abs_laps.max(axis=0)
        bool_mask = abs_laps == maxima
        mask = bool_mask.astype(np.uint8)
        for i in range(0,len(images)):
            output = cv2.bitwise_not(images[i],output, mask=mask[i])
        
        return 255-output

    def crop_stacked(img_stacked):
        combined = img_stacked[:, :, 0] + img_stacked[:, :, 1] + img_stacked[:, :, 2]
        black_idx = np.where(combined == 0)

        img_stacked[black_idx] = (0, 255, 0)
        cv2.imshow("test", img_stacked)
        cv2.waitKey(0)
        # log.info(combined[0:10])
        # log.info(black_idx)

        rows = black_idx[0]
        cols = black_idx[1]
        # upper left corner is origin, therefore max row and max col are bottom right

        min_row = min(rows)
        max_row = max(rows)
        min_col = min(cols)
        max_col = max(cols) 
        
        log.info(min_col)

        middle_pt = [round(max_row/2), round(max_col/2)]
        
        x1 = middle_pt[0] #left x val
        x2 = middle_pt[0] #right x val
        y1 = middle_pt[1] #top y val
        y2 = middle_pt[1] #bottom y val

        top_found = False
        right_found = False
        left_found = False
        bottom_found = False


        while (not top_found or not bottom_found or not right_found or not left_found) and (y1 >= min_col or y2 < max_col or x2 < max_row or x1 >= min_row):
            for x in (x1, x2):
                if combined[x][y1] == 0:
                    log.info(y1)
                    top_found = True
                if combined[x][y2] == 0:
                    log.info(y2)
                    bottom_found = True
            for y in (y1, y2):
                if combined[x2][y] == 0:
                    log.info(x2)
                    right_found = True
                if combined[x1][y] == 0:
                    log.info(x1)
                    left_found = True
            if y1 == min_col:
                top_found = True
            elif not top_found:
                y1 -= 1
            if y2 == max_col-1:
                    bottom_found = True
            elif not bottom_found:
                y2 += 1
            if x2 == max_row-1:
                right_found = True
            elif not right_found:
                x2 += 1
            if x1 == min_row:
                left_found = True
            elif not left_found:
                x1 -= 1
            # while (not right_found or not left_found) and (x2 < max_row or x1 >= min_row):
            #     for y in (y1, y2):
            #         if combined[x2][y] == 0:
            #             right_found = True
            #         if combined[x1][y] == 0:
            #             left_found = True
            #     if x1 == max_col:
            #         right_found = True
            #     else:
            #         x2 += 1
            #     if x1 == min_row:
            #         left_found = True
            #     else:
            #         x1 -= 1
            # while not left_found and x1 >= min_row:
            #     for y in (y1, y2):
            #         if combined[x1][y] == 0:
            #             left_found = True
            #             break
            #     # if not top_found:
            #     #     y1 -= 1
            #     # if not bottom_found:
            #     #     y2 += 1
            #     if x1 == min_row:
            #         left_found = True
            #     else:
            #         x1 -= 1
            # while not bottom_found and y2 < max_col:
            #     for x in (x1, x2):
            #         if combined[x][y1] == 0:
            #             top_found = True
            #             break
            #     # if not left_found:
            #     #     x1 -= 1
            #     # if not right_found:
            #     #     x2 += 1
                
            


        
        log.info(x1, x2, y1, y2)
        # row_tr = 
        # col_tr = 

        # row_br = 
        # col_br = 

        # row_bl = 
        # col_bl = 

        cropped_img = img_stacked[x1:x2,y1:y2,:]

        cv2.imwrite("cropped.jpg", cropped_img)

        log.info("test")

if __name__ == "__main__":
    image_files = os.listdir("edge_imgs")
    focusimages = []
    for img in image_files:
        focusimages.append(cv2.imread("edge_imgs/{}".format(img)))

    stacker = FocusStack()
    img = stacker.focus_stack(focusimages)


    cv2.imwrite("stackedimg.jpg", img)

#     os.chdir("c:/Users/chloe/wolkovich_s24/TreeRings/code")
#     log.info(os.getcwd())
#     img = cv2.imread("stackedimg.jpg")

#     crop_stacked(img)

#     cv2.imwrite("og.jpg", img)
#     cv2.imwrite("new.jpg", img[img.nonzero()])
#     cv2.waitKey(0)
