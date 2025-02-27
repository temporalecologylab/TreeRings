import cv2
import logging as log
import shutil
import numpy as np
import os
from pathlib import Path
from PID import AsynchronousPID 
import utils
import sample

log.basicConfig(format='%(process)d-%(levelname)s-%(message)s', level=log.INFO)

class Focus:

    def __init__(self, delete_flag, setpoint):
        self.config =  utils.load_config()

        self.DELETE_FLAG = delete_flag
        self.scale_factor = 0.05

        self.kp = self.config["focus"]["Kp"]        
        self.ki = self.config["focus"]["Ki"]        
        self.kd = self.config["focus"]["Kd"]     
        self.background_std_threshold = self.config["focus"]["BACKGROUND_STD_THRESHOLD"]  # low zoom = 0.015, high zoom = 0.125
        self.PID = AsynchronousPID(Kp=self.kp, Ki=self.ki, Kd=self.kd, setpoint=setpoint) 
        self.TESTINGLOG = []

    def find_focus(self, sample: sample.Sample, focus_queue, pid_queue, pid_lock):
        while True:
            image_files = focus_queue.get()
            pid_lock.acquire()

            #log.info("Images For focus finding: {}".format(image_files))
            if image_files == [-1]:
                focus_queue.task_done()
                break
            focused_image_name, std, nv = self.best_focused_image(image_files)
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
                shutil.copy(focused_image_name, "{}/focused_images/{}".format(sample.directory,filename))
            
            sample.background_std.append(std)
            sample.background.append(self.is_background(std))
            sample.focus_index.append(stack_number)
            sample.nvar.append(nv)

            if not self.is_background(std):
                control_variable = self.PID.update(int(stack_number))
                log.info(f"focused image: {stack_number} control variable = {control_variable}")
                update_z = self.adjust_focus(control_variable, self.scale_factor)
                pid_queue.put(update_z)
            else:
                pid_queue.put(0)
                log.info("Background detected, ignore focus index score")
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

    def best_focused_image(self, image_filenames, delete = False):
        best_image_filepath = None
        best_var = 0
        vars = []

        for image_name in image_filenames:
            image = cv2.imread(image_name, cv2.IMREAD_GRAYSCALE)
            if type(image) == np.ndarray:
                var = self.compute_variance(image)
                vars.append(var)
                if var > best_var:
                    best_image_filepath = image_name
                    best_var = var
            
        std = np.std(vars)

        # log.info(image_filenames)

        if delete:
            self.delete_unfocused(image_filenames)
        return best_image_filepath, std, vars
        

    def delete_unfocused(self, images_to_delete):
        for file_name in images_to_delete:
            os.remove(file_name)
    
    def is_background(self, std):
        # High zoom, 0.125 seemed to work. Low zoom, 0.015 seems to work
        if std > self.background_std_threshold:
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


if __name__ == "__main__":

    import glob
    import matplotlib.pyplot as plt

    filename_grep_1 = "C:\\code\\TreeRings\\code\\images_1\\image_*"
    filename_grep_2 = "C:\\code\\TreeRings\\code\\images_2\\image_*"
    filename_grep_3 = "C:\\code\\TreeRings\\code\\images_3\\image_*"
    filename_grep_4 = "C:\\code\\TreeRings\\code\\images_4\\image_*"
    filename_grep_5 = "C:\\code\\TreeRings\\code\\images_5\\image_*"

    filenames = glob.glob(filename_grep_2)
    # filenames.extend(glob.glob(filename_grep_2))
    # filenames.extend(glob.glob(filename_grep_3))
    # filenames.extend(glob.glob(filename_grep_4))
    # filenames.extend(glob.glob(filename_grep_5))


    def compute_variance(image):
        # adapted from macro info at https://imagejdocu.list.lu/macro/normalized_variance
        mean = np.mean(image)
        width, height = image.shape
        square_diff = (image - mean)**2
        b = np.sum(square_diff)
        normVar = b/(height * width * mean)
        return normVar
    
    def horizontal_focus_distribution(filename, n_cols):
        """Split a single image into n_cols and calculate the normalized variance for each column.

        Args:
            filename (_type_): Filename of the image to analyze.
            n_cols (_type_): Number of columns to split the image into. Must be even to split correctly.
        """
        if n_cols % 2 == 1:
            n_cols += 1

        image = cv2.imread(filename, cv2.IMREAD_GRAYSCALE)
        image = np.array(image) # seems like a silly conversion but is going to help with the math 
        # plt.imshow(image)

        # split the image into columns
        columns = np.vsplit(image, n_cols)

        best_var = 0
        vars = []
        for col in columns:
            var = compute_variance(col)
            vars.append(var)
            if var > best_var:
                best_var = var

        return vars, best_var
    

        # calculate the normalized variance of each of the columns
        
    var_per_image = []
    ids = []
    for i, filename in enumerate(filenames):
        image = cv2.imread(filename, cv2.IMREAD_GRAYSCALE)
        vars, best_var = horizontal_focus_distribution(filename, 1)
        var_per_image.append(vars[0])
        ids.append(i)
        print(filename)
        # var_2.append(vars[1])
    plt.bar(np.arange(len(var_per_image)), var_per_image)
    # plt.plot(np.arange(len(var_2)), var_2, label = 2)
    plt.legend()
    plt.show()
