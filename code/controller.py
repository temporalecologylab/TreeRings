import gantry
import focus
import cookie
import camera
import logging as log
from datetime import datetime
import time
import math
import queue
from threading import Thread
from pathlib import Path


class Controller:

    def __init__(self, image_width_mm, image_height_mm):
        
        #Objects
        #TODO: logic for when we have many cookies on one platform
        self.cookies = []
        self.gantry = gantry.Gantry()
        self.camera = camera.Camera()
        self.focus = focus.Focus()

        #attributes
        self.image_height_mm = image_height_mm
        self.image_width_mm = image_width_mm
        self.directory = "."

    def quit(self):
        log.info("Ending Camera Stream")
        self.camera.stop_pipeline()
        log.info("Disconnecting serial port")
        self.gantry.serial_disconnect_port()

    def set_image_height_mm(self, height):
        self.image_height_mm = height
    
    def set_image_width_mm(self, width):
        self.image_width_mm = width

    def set_directory(self, dir):
        self.directory = dir

    #### SERPENTINE METHODS ####
    
    def capture_cookie(self):
        rows, cols, y_dist, x_dist = self.calculate_grid()
        focus_queue = queue.Queue()
        
        #set directories
        if self.directory == ".":
            dirtime = datetime.now().strftime("%H_%M_%S")
            Path("./cookiecapture_{}".format(dirtime)).mkdir()
            self.set_directory("./cookiecapture_{}".format(dirtime))
        Path("{}/focused_images".format(self.directory)).mkdir(exist_ok=True)

        gantry_thread = Thread(target=self.capture_grid_photos, args=(focus_queue, rows, cols, y_dist, x_dist))
        focus_thread = Thread(target=self.focus.find_focus, args=(focus_queue, self.directory))
        gantry_thread.start()
        focus_thread.start()
        
        gantry_thread.join()	
        focus_queue.join()    	
        focus_thread.join()

    def calculate_grid(self): 
        if len(self.cookies) > 0:
            cookie = self.cookies[-1]
            overlap_x = round(self.image_width_mm * cookie.percent_overlap / 100, 3)
            overlap_y = round(self.image_height_mm * cookie.percent_overlap / 100, 3)

            log.info("overlap x: {}".format(overlap_x))
            log.info("overlap y: {}".format(overlap_y))
            
            x_step_size = self.image_width_mm - overlap_x
            y_step_size = self.image_height_mm - overlap_y 

            log.info("x_step_size x: {}".format(x_step_size))
            log.info("y_step_size y: {}".format(y_step_size))

            x_steps = math.ceil(cookie.width / x_step_size)
            y_steps = math.ceil(cookie.height / y_step_size)

            log.info("x_steps: {}".format(x_steps))
            log.info("y_steps: {}".format(y_steps))
        
        return y_steps, x_steps, y_step_size, x_step_size
    
    def capture_grid_photos(self, focus_queue: queue.Queue, rows: int, cols: int, y_dist, x_dist, z_steps=9, pause=2):
        # for loop capture
        # Change feed rate back to being slow
        self.set_feed_rate(1)
        
        for row in range(rows):
            # for last column, we only want to take photo, not move.
            for col in range(cols - 1):
                # Odd rows go left
                if row % 2 == 1:
                    imgs = self.capture_images_multiple_distances(0.1, z_steps, row, cols - col -1)
                    self.gantry.jog_x(-x_dist)
                # Even rows go right
                else:
                    imgs = self.capture_images_multiple_distances(0.1, z_steps, row, col)
                    self.gantry.jog_x(x_dist)
                time.sleep(pause)
                focus_queue.put(imgs)

            # Take final photo in row before jogging down
            if row % 2 == 1:
                imgs = self.capture_images_multiple_distances(0.1, z_steps, row, 0)
                focus_queue.put(imgs)

            else:
                imgs = self.capture_images_multiple_distances(0.05, z_steps, row, cols - 1)
                focus_queue.put(imgs)

            self.gantry.jog_y(-y_dist)
            time.sleep(pause)
        focus_queue.put([-1])

    def capture_images_multiple_distances(self, step_size_mm: float, image_count_odd: int, row, col, pause = 2):
        image_filenames = []

        if image_count_odd // 2 == 0:
            return "MUST BE ODD"
        
        z_offset = round(math.floor(image_count_odd / 2) * step_size_mm, 3)

        # go to the bottom of the range 
        self.gantry.jog_z(-z_offset)
        
        #take first photo in stack
        file_location = f"{self.directory}/frame_{row}_{col}_0.tiff"
        image_filenames.append(file_location)
        time.sleep(pause)
        self.camera.save_frame(file_location)
        
        # move upwards by a step, take a photo, then repeat
        for i in range(1, image_count_odd):
            self.gantry.jog_z(step_size_mm)
            time.sleep(pause)
            file_location = f"{self.directory}/frame_{row}_{col}_{i}.tiff"
            image_filenames.append(file_location)
            self.camera.save_frame(file_location)

        # return to original position
        self.gantry.jog_z(-z_offset)
        time.sleep(pause)
        return image_filenames

    #### JOG METHODS ####

    def jog_x(self, dist):
        self.gantry.jog_x(dist)

    def jog_y(self, dist):
        self.gantry.jog_y(dist)

    def jog_z(self, dist):
        self.gantry.jog_z(dist)

    def set_feed_rate(self, mode):
        # Slow mode
        if mode == 1:
            self.gantry.feed_rate_xy = 200
            self.gantry.feed_rate_z = 15
        # Fast mode
        if mode == 2:
            self.gantry.feed_rate_xy = 500
            self.gantry.feed_rate_z = 75

    #### CAMERA METHODS ####

    def cb_capture_image(self):
        name = "{}/image_{}.tiff".format(self.directory, datetime.now().strftime("%H_%M_%S"))
        self.camera.save_frame(name)
        log.info("Saving {}".format(name))
    
    #### COOKIE METHODS ####

    def add_cookie_sample(self, width, height, overlap):
        ck = cookie.Cookie(width, height, overlap)
        self.cookies.append(ck)
        log.info("Adding Cookie \nW: {}\nH: {}\nO: {}\n".format(width, height,overlap))

   #### GANTRY METHODS ####

    def serial_connect(self):
        self.gantry.serial_connect_port()

    def cb_pause_g_code(self):
        self.gantry.pause()

    def cb_resume_g_code(self):
        self.gantry.resume()

    def cb_homing_g_code(self):
        self.gantry.homing_sequence() 
        
