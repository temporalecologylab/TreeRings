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
from threading import Thread, Lock, Event
from multiprocessing import Process
from pathlib import Path
import json


class Controller:

    def __init__(self, image_width_mm, image_height_mm):
        #Settings for capturing images from multiple distances
        self.n_images = 9 #make sure you're not going faster than the frame rate of the GStreamer feed... 
        self.height_range = 1
        
        #Objects
        self.cookies = []
        self._gantry = gantry.Gantry()
        self.camera = camera.Camera()
        self.focus = focus.Focus(delete_flag=True, setpoint=round(self.n_images / 2))
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
    
    def capture_cookie(self, cookie: cookie.Cookie, progress_callback, stop_capture):

        while not stop_capture.is_set():
            rows, cols, y_dist, x_dist = self.calculate_grid(cookie)
            focus_queue = queue.Queue()
            pid_queue = queue.Queue()
            pid_lock = Lock()

            self.focus.set_setpoint(round(self.n_images/2))

            #set directories
            species = cookie.species
            id1 = cookie.id1
            id2 = cookie.id2

            dirtime = datetime.now().strftime("%H_%M_%S")
            directory = "./{}_{}_{}_{}".format(species, id1, id2, dirtime)
            Path(directory).mkdir()
            self.set_directory(directory)

            start_time = time.time()

            x, y, z = cookie.get_center_location()
            gantry_thread = Thread(target=self.capture_grid_photos, args=(focus_queue, pid_queue, pid_lock, rows, cols, y_dist, x_dist, z, self.n_images, self.height_range, progress_callback, stop_capture))
            focus_thread = Thread(target=self.focus.find_focus, args=(focus_queue, pid_queue, pid_lock, self.directory))
            gantry_thread.start()
            focus_thread.start()
            
            gantry_thread.join()	
            focus_queue.join()    	
            focus_thread.join()

            end_time = time.time()
            elapsed_time = end_time - start_time
            num_images = rows * cols

            self.create_metadata(cookie, elapsed_time, num_images, rows, cols)

    def capture_all_cookies(self, progress_callback, stop_capture):
        while not stop_capture.is_set():
            for i in range(len(self.cookies)):
                cookie = self.cookies.pop(-1)
                progress_callback((True, True, "{}_{}_{}".format(cookie.species, cookie.id1, cookie.id2)))
                self.navigate_to_cookie(cookie)
                self.capture_cookie(cookie, progress_callback, stop_capture)

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
    
    def capture_grid_photos(self, focus_queue: queue.Queue, pid_queue: queue.Queue, pid_lock, rows: int, cols: int, y_dist, x_dist, z_start, n_images, height_range, progress_callback, stop_capture):
        # for loop capture
        # Change feed rate back to being slow
        self.set_feed_rate(1)
        while True and not stop_capture.is_set():
            img_num = 0
            for row in range(rows):
                if stop_capture.is_set():
                    break
                # for last column, we only want to take photo, not move.
                for col in range(cols - 1):
                    start_stack = time.time()
                    # Odd rows go left
                    if stop_capture.is_set():
                        break

                    if row % 2 == 1:
                        imgs = self.capture_images_multiple_distances(n_images, self._gantry.feed_rate_z, height_range, 0.2, row, cols - col - 1, z_start)
                        pid_lock.acquire()
                        self.jog_relative_x(-x_dist)
                        pid_lock.release()
                    # Even rows go right
                    else:
                        imgs = self.capture_images_multiple_distances(n_images, self._gantry.feed_rate_z, height_range, 0.2, row, col, z_start)
                        pid_lock.acquire()
                        self.jog_relative_x(x_dist)
                        pid_lock.release()

                    focus_queue.put(imgs)

                    update_z = pid_queue.get()
                    log.info(f"z move for update {update_z}")
                    z_start+=update_z
                    pid_queue.task_done()

                    # Allow for PID calculations to continue while x is still jogging. Imagine a very large x jog which takes a  while.
                    self._gantry.block_for_jog()
                    img_num=img_num+1
                    elapsed_time = time.time() - start_stack
                    progress_callback((elapsed_time, img_num, rows*cols))

                start_stack = time.time()
                # Take final photo in row before jogging down
                if stop_capture.is_set():
                    break
                
                if row % 2 == 1:
                    # imgs = self.capture_images_multiple_distances(0.1, z_steps, row, 0)
                    imgs = self.capture_images_multiple_distances(n_images, self._gantry.feed_rate_z, height_range, 0.2, row, 0, z_start)
                else:
                    # imgs = self.capture_images_multiple_distances(0.05, z_steps, row, cols - 1)
                    imgs = self.capture_images_multiple_distances(n_images, self._gantry.feed_rate_z, height_range, 0.2, row, cols - 1, z_start)
                focus_queue.put(imgs)

                pid_lock.acquire()    
                self.jog_relative_y(-y_dist)
                pid_lock.release()

                update_z = pid_queue.get()
                log.info(f"z move for update {update_z}")
                z_start += update_z
                pid_queue.task_done()

                self._gantry.block_for_jog()
                img_num=img_num+1
                elapsed_time = time.time() - start_stack
                progress_callback((elapsed_time, img_num, rows*cols))    

            focus_queue.put([-1])
            break

    def capture_images_multiple_distances(self, image_count, feed_rate, r, acceleration_buffer, row, col, z_start):
        """A method to move the camera through a Z range to allow for multiple images to be taken. This implementation is designed to reduce motion blur by taking advantage of a slow feed rate and avoiding a deceleration then sleep cycle to get an in focus image.

        Args:
            image_count (int): How many images do you want to take throughout the range
            feed_rate (int): What is the feed rate of the Z-axis in mm/min
            r (float): The distance in mm between the first and last image.
            acceleration_buffer (float): Extra distance beyond the range to allow for the z-axis to reach constant velocity
            row (int): Row location of where on the cookie grid the images are in 
            col (int): Col location '                                           '
        """
        # adding absolute jogging to start point because there is slight stochasticity between relative jogs. Resulting in drift
        _, _, z = self._gantry.get_xyz()
        start_z = z

        self.jog_absolute_z(start_z)
        self._gantry.block_for_jog()

        image_filenames = []

        time_between_photos_s = r / feed_rate * 60 / image_count # mm / (mm / min) * (s / min) is the dim analysis for units of seconds
        time_zero_acceleration_s = acceleration_buffer / feed_rate * 60

        # Jog to the top of the range + acceleration buffer
        top = (r / 2) + acceleration_buffer
        self.jog_relative_z(top)
        self._gantry.block_for_jog()

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
        
        # This might take a while so do not send the next jog until we finish the previous
        self._gantry.block_for_jog()
        # Return to original location
        self.jog_absolute_z(z_start)
        self._gantry.block_for_jog()        

        return image_filenames
    
    def create_metadata(self, cookie, elapsed_time, image_count, rows, cols):
        cookie_size = cookie.height * cookie.width
        camera_fov = self.image_height_mm * self.image_width_mm
        pixels = self.camera.h_pixels * self.camera.w_pixels
        dpi = self.camera.w_pixels/self.image_width_mm * 25.4  
        metadata = {
            "species": cookie.species,
            "rows": rows,
            "cols": cols,
            "size": rows * cols,
            "id1": cookie.id1,
            "id2": cookie.id2,
            "elapsed_time": elapsed_time,
            "DPI": round(dpi,2),
            "photo_count": image_count,
            "image_height_mm": self.image_height_mm,
            "image_width_mm": self.image_width_mm,
            "cookie_height_mm": cookie.height,
            "cookie_width_mm":  cookie.width,
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

    def jog_absolute_xy(self, x, y):
        self._gantry.jog_absolute_xy(x, y)

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

        log.info("Navigating to {}, X{}Y{}Z{}".format(cookie.species, x, y, z))
        # Wait until we get to the cookie location
        self._gantry.block_for_jog()

    def traverse_cookie_boundary(self, cookie_width, cookie_height):
        
        try: 
            x, y, z = self._gantry.get_xyz()

            l_x = x - (cookie_width / 2)
            r_x = x + (cookie_width / 2)
            b_y = y - (cookie_height/ 2)
            t_y = y + (cookie_height / 2)

            tl = (l_x, t_y)
            tr = (r_x, t_y)
            bl = (l_x, b_y)
            br = (r_x, b_y)

            # Go to top left, then move clockwise until return to tl
            self.jog_absolute_xy(tl[0], tl[1])
            self._gantry.block_for_jog()

            self.jog_absolute_x(tr[0])
            self._gantry.block_for_jog()
            self.jog_absolute_y(br[1])
            self._gantry.block_for_jog()
            self.jog_absolute_x(bl[0])
            self._gantry.block_for_jog()
            self.jog_absolute_y(tl[1])
            self._gantry.block_for_jog()

            # go back to center
            self.jog_absolute_xyz(x, y, z)
            self._gantry.block_for_jog()
        except:
            log.info("cookie not defined")


    #### CAMERA METHODS ####

    def cb_capture_image(self, name = None):
        if name is None:
            name = "{}/image_{}.tiff".format(self.directory, datetime.now().strftime("%H_%M_%S_%f"))
        self.camera.save_frame(name)
        log.info("Saving {}".format(name))
        return name
    
    #### COOKIE METHODS ####

    def add_cookie_sample(self, width, height, overlap, species, id1, id2, notes):
        center_x, center_y, center_z = self._gantry.get_xyz()

        tl_x = center_x - (width/2)
        tl_y = center_y + (height/2)
        tl_z = center_z

        if overlap == '':
            overlap = 50
        if species == '':
            species = "na"
        if id1 == '':
            id1 = "na"
        if id2 == '':
            id2 = "na"

        #path_name = self.cb_capture_image()
        ck = cookie.Cookie(width, height, species, id1, id2, notes, overlap, center_x, center_y, center_z, tl_x, tl_y, tl_z)
        self.cookies.append(ck)

    def get_cookies(self):
        return self.cookies
    
    def set_cookies(self, cookies):
        self.cookies=cookies

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
        
