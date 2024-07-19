import cv2
import logging as log
import shutil
import numpy as np
import os
from PID import AsynchronousPID 

log.basicConfig(format='%(process)d-%(levelname)s-%(message)s', level=log.INFO)

class Focus:

    def __init__(self, delete_flag, n_images):
        self.DELETE_FLAG = delete_flag
        self.sat_min = 0
        self.sat_max = 255
        self.PID = AsynchronousPID(Kp=1.0, Ki=0.1, Kd=0.05, setpoint=n_images) # Setpoint?? depends on camera i think

    def set_sat_min(self, saturation_min):
        self.sat_min = saturation_min
    
    def set_sat_max(self, saturation_max):
        self.sat_max = saturation_max

    def find_focus(self, focus_queue, pid_queue, pid_lock, directory):
        while True:
            image_files = focus_queue.get()
            with pid_lock:
                log.info("Images For focus finding: {}".format(image_files))
                if image_files == [-1]:
                    focus_queue.task_done()
                    break

                focused_image_name = self.best_focused_image(image_files)
                image_name = focused_image_name.split("/")[-1].split("_")
                extract_row = image_name[1]
                extract_col = image_name[2]
                stack_number = image_name[3]
                filename = "focused_{}_{}.tiff".format(extract_row, extract_col) 
                
                if self.DELETE_FLAG:
                    image_files.remove(focused_image_name)
                    self.delete_unfocused(image_files)
                else: 
                    shutil.copy(focused_image_name, "{}/focused_images/{}".format(directory,filename))
                image = cv2.imread(focused_image_name)
                if self.is_background(image):
                    control_variable = self.PID.update(stack_number)
                    log.info(f"control variable = {control_variable}")
                    update_z = self.adjust_focus(control_variable, 0.05)
                    pid_queue.put(update_z)
                focus_queue.task_done()
        
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
        for file_name in images_to_delete:
            os.remove(file_name)

    def hsv_mask(self, image):
        imgHSV = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

        s_channel = imgHSV[:,:,1]
        mask = cv2.inRange(s_channel, self.sat_min, self.sat_max)
        res =cv2.bitwise_and(image, image, mask=mask)
        return res
    
    def is_background(self, image):
        masked_image = self.hsv_mask(image)

        nan_image=masked_image.astype('float')
        nan_image[nan_image==0]=np.nan

        # if 25% of image is nan, count as a background image
        if np.count_nonzero(np.isnan(nan_image)) > (nan_image.size * 0.25):
            return True
        return False
    
    def adjust_focus(self, control_signal, scale_factor):
        # Convert the control signal to millimeters of movement using the scale factor
        movement_mm = control_signal * scale_factor
        return movement_mm  

    ''' pid moment:
        need to update from controller, methods go in focus? '''