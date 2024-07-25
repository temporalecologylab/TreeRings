import cv2
import logging as log
import shutil
import numpy as np
import os
from pathlib import Path


log.basicConfig(format='%(process)d-%(levelname)s-%(message)s', level=log.INFO)

class Focus:

    def __init__(self, delete_flag):
        self.DELETE_FLAG = delete_flag

    def find_focus(self, img_pipeline, directory):
        while True:
            image_files = img_pipeline.get()
            log.info("Images For focus finding: {}".format(image_files))
            if image_files == [-1]:
                img_pipeline.task_done()
                break
                      
            image_name = image_files[0].split("/")[-1].split("_")
            extract_row = image_name[1]
            extract_col = image_name[2]
            filename = "focused_{}_{}.tiff".format(extract_row, extract_col) 
            focused_image_name = self.best_focused_image(image_files)
            if self.DELETE_FLAG:
                image_files.remove(focused_image_name)
                self.delete_unfocused(image_files)
            else: 
                Path("{}/focused_images".format(self.directory)).mkdir(exist_ok=True)
                shutil.copy(focused_image_name, "{}/focused_images/{}".format(directory,filename))


            img_pipeline.task_done()
        
    def compute_variance(self, image):
        # adapted from macro info at https://imagejdocu.list.lu/macro/normalized_variance
        mean = np.mean(image)
        width, height = image.shape
        square_diff = (image - mean)**2
        b = np.sum(square_diff)
        normVar = b/(height * width * mean)
        return normVar

    def best_focused_image(self, images):
        best_image_filepath = []
        best_var = 0

        for image_name in images:
            image = cv2.imread(image_name, cv2.IMREAD_GRAYSCALE)
            if type(image) == np.ndarray:
                var = self.compute_variance(image)
                if var > best_var:
                    best_image_filepath = image_name
                    best_var = var
        return best_image_filepath     

    def delete_unfocused(self, images_to_delete):
        for im_name in images_to_delete:
            os.remove(im_name)
