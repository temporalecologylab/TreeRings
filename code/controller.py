import gantry
import focus
import cookie
import camera
import logging as log
import datetime
import time
import math
import queue
from threading import Thread


class Controller:

    def __init__(self, image_width_mm, image_height_mm):
        
        #TODO: logic for when we have many cookies on one platform
        self.cookies = []
        self.gantry = gantry.Gantry()
        self.camera = camera.Camera()

        #attributes
        self.image_height_mm = image_height_mm
        self.image_width_mm = image_width_mm

        self.directory = "./"

    def quit(self):
        log.info("Ending Camera Stream")
        self.camera.end_camera_filesave()
        log.info("Disconnecting serial port")
        self.gantry.serial_disconnect_port()

    def set_image_height_mm(self, height):
        self.image_height_mm = height
    
    def set_image_width_mm(self, width):
        self.image_width_mm = width

    def set_directory(self, dir):
        self.directory = dir

    #### SERPENTINE METHODS ####

    def calculate_grid(self): 
        if len(self.cookies) > 0:
            overlap_x = round(self.image_width_mm * self.cookie.percent_overlap / 100, 3)
            overlap_y = round(self.image_height_mm * self.cookie.percent_overlap / 100, 3)

            log.info("overlap x: {}".format(overlap_x))
            log.info("overlap y: {}".format(overlap_y))
            # TODO: add logic / user input / something to move z to be in focus
            x_step_size = self.image_width_mm - overlap_x
            y_step_size = self.image_height_mm - overlap_y 

            log.info("x_step_size x: {}".format(x_step_size))
            log.info("y_step_size y: {}".format(y_step_size))

            x_steps = math.ceil(cookie.width / x_step_size)
            y_steps = math.ceil(cookie.height / y_step_size)

            log.info("x_steps: {}".format(x_steps))
            log.info("y_steps: {}".format(y_steps))
        
        return y_steps, x_steps, y_step_size, x_step_size

    def capture_cookie(self):
        # calculating row, col, x_move, y_move
        rows, cols, y_dist, x_dist = self.calculate_grid(self)
        img_pipeline = queue.Queue()

        gantry_thread = Thread(target=self.capture_grid_photos, args=(img_pipeline, rows, cols, y_dist, x_dist))
        focus_thread = Thread(target=self.focus.find_focus, args=(img_pipeline, self.directory))
        gantry_thread.start()
        #focus_thread.start()
        
        gantry_thread.join()	
        img_pipeline.join()    	
        #focus_thread.join()
    
    def capture_grid_photos(self, img_pipeline, rows, cols, y_dist, x_dist, z_steps=7, pause=2):
        # for loop capture
        for row in rows:
            for col in cols:
                if col % 2 == 1:
                    self.capture_images_multiple_distances(0.1, z_steps, cols - col -1, row)
                    self.gantry.jog_x(-x_dist)
                else:
                    self.capture_images_multiple_distances(0.1, z_steps, col, row)
                    self.gantry.jog_x(x_dist)
                time.sleep(pause)
                img_pipeline.put([row, col, z_steps])
            self.gantry.jog_y(-y_dist)
            time.sleep(pause)

    def capture_images_multiple_distances(self, step_size_mm: float, image_count_odd: int, x_loc, y_loc, pause = 1):
        images = []
        dist = 0 #distance from zero 

        if image_count_odd // 2 == 0:
            return "MUST BE ODD"
        
        z_offset = round(math.floor(image_count_odd / 2) * step_size_mm, 3)

        # go to the bottom of the range 
        self.jog_z(-z_offset)
        
        #take first photo in stack
        file_location = f"{self.directory}/frame_{x_loc}_{y_loc}_{0}.jpg"
        log.info("Stack image {}".format(file_location))
        self.save_image(file_location)
        time.sleep(pause)
        
        # move upwards by a step, take a photo, then repeat
        for i in range(1, image_count_odd):
            self.jog_z(step_size_mm)
            time.sleep(pause)
            file_location = f"{self.directory}/frame_{x_loc}_{y_loc}_{i}.jpg"
            log.info("Stack image {}".format(file_location))
            self.camera.save_frame(file_location)

        # return to original position
        self.jog_z(-z_offset)
        time.sleep(pause)

    #### CAMERA METHODS ####

    def cb_capture_image(self):
        name = "{}/image_{}.jpg".format(self.directory, datetime.now().strftime("%H_%M_%S"))
        self.camera.save_frame(name)
        log.info("Saving {}".format(name))
    
    #### COOKIE METHODS ####

    def add_cookie_sample(self, width, height, overlap):
        self.cookie = cookie.Cookie(width, height, overlap)
        self.cookies.append(cookie)
        log.info("Adding Cookie \nW: {}\nH: {}\nO: {}\n".format(width, height,overlap))

   #### GANTRY METHODS ####

    def serial_connect(self):
        self.gantry.serial_connect_port()

    def jog_y_plus(self):
        log.info("jog +{} mm y".format(self.jog_distance))
        self.gantry.jog_fast_y(self.jog_distance)

    def jog_y_minus(self):
        log.info("jog -{} mm y".format(self.jog_distance))
        self.gantry.jog_fast_y(self.jog_distance * -1)
    
    def jog_x_plus(self):
        log.info("jog +{} mm x".format(self.jog_distance))
        self.gantry.jog_fast_x(self.jog_distance)

    def jog_x_minus(self):
        log.info("jog -{} mm x".format(self.jog_distance))
        self.gantry.jog_fast_x(self.jog_distance * -1)
    
    def jog_z_plus(self):
        log.info("jog +{} mm z".format(self.jog_distance))
        self.gantry.jog_fast_z(self.jog_distance)

    def jog_z_minus(self):
        log.info("jog -{} mm z".format(self.jog_distance))
        self.gantry.jog_fast_z(self.jog_distance * -1)

    def cb_pause_g_code(self):
        self.gantry.pause()

    def cb_resume_g_code(self):
        self.gantry.resume()

    def cb_homing_g_code(self):
        self.gantry.homing_sequence() 
        