import gantry
import focus
import cookie
import camera
import stitcher
import logging as log
from datetime import datetime
import time
import math
import queue
from threading import Thread, Lock
from multiprocessing import Process
from pathlib import Path
import json


class Controller:

    def __init__(self, image_width_mm, image_height_mm):
        
        #Objects
        #TODO: logic for when we have many cookies on one platform
        self.cookies = []
        self._gantry = gantry.Gantry()
        self.camera = camera.Camera()
        self.focus = focus.Focus(delete_flag=True, setpoint=5)
        self.stitcher = stitcher.Stitcher()

        #attributes
        self.image_height_mm = image_height_mm
        self.image_width_mm = image_width_mm
        self.directory = "."

    def quit(self):
        log.info("Ending Camera Stream")
        self.camera.stop_pipeline()
        log.info("Disconnecting serial port")
        self._gantry.quit()

    def set_image_height_mm(self, height):
        self.image_height_mm = height
    
    def set_image_width_mm(self, width):
        self.image_width_mm = width

    def set_directory(self, dir):
        self.directory = dir

    #### SERPENTINE METHODS ####
    
    def capture_cookie(self, cookie):
        rows, cols, y_dist, x_dist = self.calculate_grid(cookie)
        focus_queue = queue.Queue()
        pid_queue = queue.Queue()
        pid_lock = Lock()
        n_images = 9


        self.focus.set_sat_min(cookie.saturation_max)

        #set directories

        dirtime = datetime.now().strftime("%H_%M_%S")
        Path("./cookiecapture_{}".format(dirtime)).mkdir()
        self.set_directory("./cookiecapture_{}".format(dirtime))

        start_time = time.time()

        gantry_thread = Thread(target=self.capture_grid_photos, args=(focus_queue, pid_queue, pid_lock, rows, cols, y_dist, x_dist, n_images))
        focus_thread = Thread(target=self.focus.find_focus, args=(focus_queue, pid_queue, pid_lock, self.directory))
        gantry_thread.start()
        focus_thread.start()
        
        gantry_thread.join()	
        focus_queue.join()    	
        focus_thread.join()

        end_time = time.time()
        elapsed_time = end_time - start_time
        num_images = rows * cols

        self.create_metadata(cookie, elapsed_time, num_images)

    def capture_all_cookies(self):
        for i in range(len(self.cookies)):
            cookie = self.cookies.pop(-1)
            self.navigate_to_cookie(cookie)
            self.capture_cookie(cookie)

    def calculate_grid(self, cookie): 
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
    
    def capture_grid_photos(self, focus_queue: queue.Queue, pid_queue: queue.Queue, pid_lock, rows: int, cols: int, y_dist, x_dist, n_images=20, pause=0):
        # for loop capture
        # Change feed rate back to being slow
        self.set_feed_rate(1)
        while True: 
            for row in range(rows):
                
                # for last column, we only want to take photo, not move.
                for col in range(cols - 1):
                    # Odd rows go left
                    if row % 2 == 1:
                        imgs = self.capture_images_multiple_distances(n_images, self._gantry.feed_rate_z, 1, 0.2, row, cols - col - 1)
                        pid_lock.acquire()
                        self.jog_relative_x(-x_dist)
                        pid_lock.release()
                    # Even rows go right
                    else:
                        imgs = self.capture_images_multiple_distances(n_images, self._gantry.feed_rate_z, 1, 0.2, row, col)
                        pid_lock.acquire()
                        self.jog_relative_x(x_dist)
                        pid_lock.release()
                    focus_queue.put(imgs)
                    time_0 = time.time()
                    update_z = pid_queue.get()
                    time_1 = time.time()

                    log.info(f"z move for update {update_z}")
                    pid_lock.acquire()
                    self.jog_relative_z(update_z)
                    pid_lock.release()
                    pid_queue.task_done()
                    
                    sleep_time = (x_dist / self._gantry.feed_rate_xy + update_z / self._gantry.feed_rate_z) * 60 - (time_1 - time_0)
                    log.info(sleep_time)
                    if sleep_time > 0:
                        time.sleep(sleep_time)
                    #pid_queue.task_done()


                # Take final photo in row before jogging down
                if row % 2 == 1:
                    # imgs = self.capture_images_multiple_distances(0.1, z_steps, row, 0)
                    imgs = self.capture_images_multiple_distances(n_images, self._gantry.feed_rate_z, 1, 0.2, row, 0)
                    focus_queue.put(imgs)
                else:
                    # imgs = self.capture_images_multiple_distances(0.05, z_steps, row, cols - 1)
                    imgs = self.capture_images_multiple_distances(n_images, self._gantry.feed_rate_z, 1, 0.2, row, cols - 1)
                    focus_queue.put(imgs)
                    
                pid_lock.acquire()    
                self.jog_relative_y(-y_dist)
                pid_lock.release()
                time_0 = time.time()
                update_z = pid_queue.get()
                time_1 = time.time()
                pid_lock.acquire()
                self.jog_relative_z(update_z)
                pid_lock.release()
                sleep_time = (y_dist / self._gantry.feed_rate_xy + update_z / self._gantry.feed_rate_z) * 60 - (time_1 - time_0)
                pid_queue.task_done()

                if sleep_time > 0:
                    time.sleep(sleep_time)

            focus_queue.put([-1])
            break

    def capture_images_multiple_distances(self, image_count, feed_rate, r, acceleration_buffer, row, col):
        """A method to move the camera through a Z range to allow for multiple images to be taken. This implementation is designed to reduce motion blur by taking advantage of a slow feed rate and avoiding a deceleration then sleep cycle to get an in focus image.

        Args:
            image_count (int): How many images do you want to take throughout the range
            feed_rate (int): What is the feed rate of the Z-axis in mm/min
            r (float): The distance in mm between the first and last image.
            acceleration_buffer (float): Extra distance beyond the range to allow for the z-axis to reach constant velocity
            row (int): Row location of where on the cookie grid the images are in 
            col (int): Col location '                                           '
        """
        image_filenames = []

        time_between_photos_s = r / feed_rate * 60 / image_count # mm / (mm / min) * (s / min) is the dim analysis for units of seconds
        time_zero_acceleration_s = acceleration_buffer / feed_rate * 60

        # Jog to the top of the range + acceleration buffer
        top = (r / 2) + acceleration_buffer
        self.jog_relative_z(top)
        sleep_time_half = top / feed_rate * 60
        log.info("Sleeping for {} to get to top".format(sleep_time_half))
        time.sleep(sleep_time_half)
        time.sleep(0.5)  # sleep to prevent excessive vibration

        # Jog to the bottom of the range. Begin taking photos after exiting the acceleration buffer zone
        bottom = -1 * (r + (acceleration_buffer * 2))
        self.jog_relative_z(bottom)
        # Sleep until outside of the acceleration
        time.sleep(time_zero_acceleration_s)
        
        # First photo at the top of the range 
        for i in range(image_count):
            file_location = f"{self.directory}/frame_{row}_{col}_{i}.tiff"
            image_filenames.append(file_location)
            self.camera.save_frame(file_location)
            time.sleep(time_between_photos_s)
            
        time.sleep(time_zero_acceleration_s)
        # Return to original location
        middle = top
        self.jog_relative_z(middle)
        # wait until we get back to the center 

        log.info("Sleeping for {} to get back to center".format(sleep_time_half))
        
        time.sleep(sleep_time_half)

        return image_filenames
    
    def create_metadata(self, cookie, elapsed_time, image_count):
        cookie_size = cookie.height * cookie.width
        camera_fov = self.image_height_mm * self.image_width_mm
        pixels = self.camera.h_pixels * self.camera.w_pixels
        dpi = self.camera.w_pixels/self.image_width_mm * 25.4  
        metadata = {
            "species": cookie.species,
            "size": cookie_size,
            "id1": cookie.id1,
            "id2": cookie.id2,
            "elapsed_time": elapsed_time,
            "DPI": dpi,
            "photo_count": image_count,
            "camera_fov": camera_fov, 
            "camera_pixels": pixels,
            "notes": cookie.notes
        }

        with open ("{}/metadata.json".format(self.directory), "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=4)

    #### JOG METHODS ####

    def jog_relative_x(self, dist):
        self._gantry.jog_relative_x(dist)

    def jog_relative_y(self, dist):
        self._gantry.jog_relative_y(dist)

    def jog_relative_z(self, dist):
        self._gantry.jog_relative_z(dist)
    
    def jog_absolute_x(self, pos = 5.0):
        self._gantry.jog_absolute_x(pos)

    def jog_absolute_y(self, pos):
        self._gantry.jog_absolute_y(pos)

    def jog_absolute_z(self, pos):
        self._gantry.jog_absolute_z(pos)

    def jog_absolute_xyz(self, x, y, z):
        self._gantry.jog_absolute_xyz(x, y, z)

    def set_feed_rate(self, mode):
        # Slow mode
        if mode == 1:
            self._gantry.feed_rate_xy = 300
            self._gantry.feed_rate_z = 20
        # Fast mode
        if mode == 2:
            self._gantry.feed_rate_xy = 1250
            self._gantry.feed_rate_z = 75

    def navigate_to_cookie(self, cookie):
        x, y, z = cookie.get_top_left_location()
        self.jog_absolute_xyz(x, y, z)
        rel_x = abs(self._gantry.x - x) 
        rel_y = abs(self._gantry.y - y)
        rel_z = abs(self._gantry.z - z)
        log.info("Navigating to {}, X{}Y{}Z{}".format(cookie.species, x, y, z))
        # Wait until we get to the cookie location
        if rel_z > rel_x and rel_z > rel_y:
            time.sleep(rel_z / self._gantry.feed_rate_z * 60) #seconds
        else:
            time.sleep(max([rel_x, rel_y]) / self._gantry.feed_rate_xy * 60) # seconds

    def traverse_cookie_boundary(self, cookie_height, cookie_width):
        
        x = self._gantry.x
        y = self._gantry.y
        z = self._gantry.z

        l_x = x - (cookie_width / 2)
        r_x = x + (cookie_width / 2)
        b_y = y - (cookie_height/ 2)
        t_y = y + (cookie_height / 2)

        tl = (l_x, t_y)
        tr = (r_x, t_y)
        bl = (l_x, b_y)
        br = (r_x, b_y)

        # Go to top left, then move clockwise until return to tl
        self.jog_absolute_x(tl[0])
        time.sleep(tl[0] * self._gantry.feed_rate_xy)
        self.jog_absolute_y(tl[1])
        time.sleep(tl[1] * self._gantry.feed_rate_xy)
        self.jog_absolute_x(tr[0])
        time.sleep(tr[0] * self._gantry.feed_rate_xy)
        self.jog_absolute_y(br[1])
        time.sleep(br[1] * self._gantry.feed_rate_xy)
        self.jog_absolute_x(bl[0])
        time.sleep(bl[0] * self._gantry.feed_rate_xy)
        self.jog_absolute_y(tl[1])
        time.sleep(tl[1] * self._gantry.feed_rate_xy)

        time.sleep(2)

        # go back to center
        self.jog_absolute_xyz(x, y, z)

    #### CAMERA METHODS ####

    def cb_capture_image(self):
        name = "{}/image_{}.tiff".format(self.directory, datetime.now().strftime("%H_%M_%S_%f"))
        self.camera.save_frame(name)
        log.info("Saving {}".format(name))
    
    #### COOKIE METHODS ####

    def add_cookie_sample(self, width, height, overlap, species, id1, id2, notes):
        center_x = self._gantry.x
        center_y = self._gantry.y
        center_z = self._gantry.z

        tl_x = center_x - (width/2)
        tl_y = center_y + (height/2)
        tl_z = center_z

        name = self.cb_capture_image
        ck = cookie.Cookie(width, height, species, id1, id2, notes, overlap, center_x, center_y, center_z, tl_x, tl_y, tl_z, cookie_path=name)
        self.cookies.append(ck)

   #### GANTRY METHODS ####

    def serial_connect(self):
        self._gantry.serial_connect_port()

    def cb_pause_g_code(self):
        self._gantry.pause()

    def cb_resume_g_code(self):
        self._gantry.resume()

    def cb_homing_g_code(self):
        # Move to the limit switches
        self._gantry.homing_sequence() 

        # Set the datum to work with G90 jogs 
        self._gantry.set_origin()
        
