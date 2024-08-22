import cv2
import logging as log
import shutil
import numpy as np
import os
from pathlib import Path
from PID import AsynchronousPID 

log.basicConfig(format='%(process)d-%(levelname)s-%(message)s', level=log.INFO)

class Focus:

    def __init__(self, delete_flag, setpoint):
        self.DELETE_FLAG = delete_flag
        self.scale_factor = 0.05
        self.PID = AsynchronousPID(Kp=1.0, Ki=0, Kd=0.05, setpoint=setpoint) 
        self.TESTINGLOG = []

    def find_focus(self, focus_queue, pid_queue, pid_lock, directory, background:np.array, background_std:np.array):
        while True:
            image_files = focus_queue.get()
            pid_lock.acquire()
            log.info("Images For focus finding: {}".format(image_files))
            if image_files == [-1]:
                focus_queue.task_done()
                break
            focused_image_name, std = self.best_focused_image(image_files)
            image_name = focused_image_name.split("/")[-1].split("_")
            row = int(image_name[1])
            col = int(image_name[2])
            stack_number = image_name[3].split(".")[0]
            filename = "focused_{}_{}.tiff".format(row, col)
            if self.DELETE_FLAG:
                image_files.remove(focused_image_name)
                self.delete_unfocused(image_files)
            else: 
                Path("{}/focused_images".format(self.directory)).mkdir(exist_ok=True)
                shutil.copy(focused_image_name, "{}/focused_images/{}".format(directory,filename))
            
            background_std[row][col] = std
            background[row][col] = self.is_background(std)

            if not self.is_background(std):
                control_variable = self.PID.update(int(stack_number))
                log.info(f"focused image: {stack_number} control variable = {control_variable}")
                update_z = self.adjust_focus(control_variable, self.scale_factor)
                pid_queue.put(update_z)
            else:
                pid_queue.put(0)
            focus_queue.task_done()
            pid_lock.release()
	    
        
    def compute_variance(self, image):
        # adapted from macro info at https://imagejdocu.list.lu/macro/normalized_variance
        mean = np.mean(image)
        width, height = image.shape
        square_diff = (image - mean)**2
        b = np.sum(square_diff)
        normVar = b/(height * width * mean)
        return normVar

    def best_focused_image(self, images):
        best_image_filepath = None
        best_var = 0
        vars = []

        for image_name in images:
            image = cv2.imread(image_name, cv2.IMREAD_GRAYSCALE)
            if type(image) == np.ndarray:
                var = self.compute_variance(image)
                vars.append(var)
                if var > best_var:
                    best_image_filepath = image_name
                    best_var = var

        std = np.std(vars)

        return best_image_filepath, std

    def delete_unfocused(self, images_to_delete):
        for file_name in images_to_delete:
            os.remove(file_name)
    
    def is_background(self, std):
        if std > 0.125:
            return False
        else:
            return True
    
    def set_setpoint(self, setpoint):
        self.PID.set_setpoint(setpoint)
        
    def adjust_focus(self, control_signal, scale_factor):
        # Convert the control signal to millimeters of movement using the scale factor
        movement_mm = control_signal * scale_factor
        return movement_mm  

    ''' pid moment:
        need to update from controller, methods go in focus? '''
