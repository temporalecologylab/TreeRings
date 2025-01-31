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
from typing import Callable
import utils
import numpy as np


class Controller:
    def __init__(self):
        """Abstraction of the controller which moves the gantry, gets information from the GUI, operates the camera, and determines when to stitch.
        """
        #Settings for capturing images from multiple distances
        # self.n_images = 11 #make sure you're not going faster than the frame rate of the GStreamer feed... 
        self.config = utils.load_config()
        self.n_images = self.config["controller"]["N_IMAGES_MULTIPLE_DISTANCES"] #make sure you're not going faster than the frame rate of the GStreamer feed... 
        # self.height_range = 1
        self.height_range = self.config["controller"]["HEIGHT_RANGE_MM"]
        self.acceleration_buffer = self.config["controller"]["ACCELERATION_BUFFER_MM"]
        self.stitch_sizes = self.config["controller"]["STITCH_SIZES"]
        self.slow_feed_rate_xy = self.config["controller"]["SLOW_FEED_RATE_XY"]
        self.slow_feed_rate_z = self.config["controller"]["SLOW_FEED_RATE_Z"]
        self.fast_feed_rate_xy = self.config["controller"]["FAST_FEED_RATE_XY"]
        self.fast_feed_rate_z = self.config["controller"]["FAST_FEED_RATE_Z"]
    
        #Objects
        self.cookies = []
        self._gantry = gantry.Gantry()
        self.camera = camera.Camera()
        self.focus = focus.Focus(delete_flag=True, setpoint=math.floor(self.n_images / 2))

        #attributes
        self.image_height_mm = self.config["gui"]["DEFAULT_IMAGE_HEIGHT_MM"]
        self.image_width_mm = self.config["gui"]["DEFAULT_IMAGE_WIDTH_MM"]
        self.directory = "."


    def quit(self):
        """Command to call upon quitting for clean shutdown
        """
        log.info("Ending Camera Stream")
        self.camera.stop_pipeline()
        log.info("Disconnecting serial port")
        self._gantry.quit()

    def set_image_height_mm(self, height: float):
        """Set the height of the image

        Args:
            height (float): Height in mm of the image. Helpful to have a 1mmx1mm grid on printer paper to measure
        """
        self.image_height_mm = height
    
    def set_image_width_mm(self, width: float):
        """Set the width of the image

        Args:
            width (float): Width in mm of the image. Helpful to have a 1mmx1mm grid on printer paper to measure
        """
        self.image_width_mm = width

    def set_directory(self, d: str):
        """Set directory where to save files if not wanted in default location.

        Args:
            d (str): New directory 
        """
        self.directory = d

    #### SERPENTINE METHODS ####
    
    def capture_cookie(self, cookie: cookie.Cookie, progress_callback: Callable, stop_capture: Event):
        """Abstraction to execute a capture sequence. This involves moving the the top left of the sample, traversing in a serpentining pattern 
        across the dimensions of the sample. At each step in the grid, multiple images are taken and only the most in focus is kept. 

        Args:
            cookie (cookie.Cookie): Instance of a sample to be captured
            progress_callback (Callable): GUI Callback to update progress bar 
            stop_capture (Event): Event to stop capture after the current image sequence 
        """

        while not stop_capture.is_set():
            focus_queue = queue.Queue()
            pid_queue = queue.Queue()
            pid_lock = Lock()

            self.focus.set_setpoint(round(self.n_images/2))

            #set directories
            species = cookie.species
            id1 = cookie.id1
            id2 = cookie.id2

            self.set_directory(cookie.directory)

            start_time = time.time()
        
            gantry_thread = Thread(target=self.capture_grid_photos, args=(cookie.coordinates, cookie.directory, cookie.targets_top, cookie.targets_bot, focus_queue, pid_queue, pid_lock, cookie.rows, cookie.cols, self.n_images, self.height_range, progress_callback, stop_capture))
            focus_thread = Thread(target=self.focus.find_focus, args=(focus_queue, pid_queue, pid_lock, cookie.directory, cookie.nvar, cookie.focus_index, cookie.background, cookie.background_std))
            gantry_thread.start()
            focus_thread.start()
            
            gantry_thread.join()	
            focus_queue.join()    	
            focus_thread.join()

            end_time = time.time()
            elapsed_time = end_time - start_time

            self.create_metadata(cookie, elapsed_time)
            
            return
            #stop_capture.set()

    def capture_all_cookies(self, progress_callback: Callable, stop_capture: Event):
        """Callable for the GUI to iterate through all cookies. For multiple cookie capture.

        Args:
            progress_callback (Callable): GUI widget to update progress bar
            stop_capture (Event): Event to stop capture as soon as possible
        """
        while not stop_capture.is_set():
            for i in range(len(self.cookies)):
                cookie = self.cookies.pop(-1)
                width_est_pixels = cookie.width / cookie.image_width_mm * self.camera.w_pixels 
                height_est_pixels = cookie.height / cookie.image_height_mm * self.camera.h_pixels
                max_filesize_est = width_est_pixels * height_est_pixels * 3 / 10e6 # megabytes
                log.info("MAX FILE SIZE ESTIMATE {} MB".format(round(max_filesize_est, 2)))
                progress_callback((True, True, "{}_{}_{}".format(cookie.species, cookie.id1, cookie.id2)))
                # self.navigate_to_cookie_tl(cookie)
                self.capture_cookie(cookie, progress_callback, stop_capture)
                
                # Only stitch if the capture complete successfully
                if not stop_capture.is_set():
                    print('stitching frames')
                    self.stitch_frames(cookie.directory)
                if len(self.cookies) == 0:
                    stop_capture.set()

            return

    def stitch_frames(self, frame_dir: str):
        """Stitch together frames into a mosaic. Not perfect yet as retrofitting Stitch2d is slightly cumbersome. If running into stitching issues, such as 'Killed' 
        or OOM, please try stitching using a more power computer with 16 GB of rame or something. This is a decently high priority to fix.

        Args:
            frame_dir (str): Directory of where the frames are. 
        """
        for size in self.stitch_sizes:
            st = stitcher.Stitcher(frame_dir) 
            #st.stitch(resize=size)
            try:
                st.stitch(resize = size)
            except RuntimeError:
                print("Cannot align with this resize value.")
            except stitcher.MaxFileSizeException:
                print("Max file size met, no longer trying to stitch")
                break
            except Exception as e:
                print(e)
                print("Unexpected exception, potentially too many files open")
            finally:
                st.delete_dats()
                del st
    
    def capture_grid_photos(self, coordinates: list, d: Path, targets_top:np.array, targets_bot: np.array, focus_queue: queue.Queue, pid_queue: queue.Queue, pid_lock, rows:int, cols:int, n_images: int, height_range: float, progress_callback: Callable, stop_capture: Event, is_core: bool = True, is_vertical: bool = True):
        """Command to traverse the sample and capture an image at each location. 

        Args:
            coordinates (list): Container for holding the coordinates of where each image was taken. Useful for debugging.
            d (Path): Directory to save.
            target_top (np.array): Targets for images, each column represents (X, Y, Z, row, col), execute in this order
            target_bot (np.array): Targets for images, each column represents (X, Y, Z, row, col), execute in this order
            focus_queue (queue.Queue): Queue to have images added to for the focus thread to parse which is the most in focus.
            pid_queue (queue.Queue): Queue to determine if the z height needs to be adjusted to stay in focus.
            pid_lock (_type_): Lock to prevent race conditions
            rows (int): Row count in the grid of images
            cols (int): Column count in the grid of images
            y_dist (float): Distance to jog in y direction per step
            x_dist (float): Distance to jog in x direction per step
            z_start (float): Absolute z location to start capturing
            n_images (int): Count of images to take at different distances when focusing 
            height_range (float): The range between the maximum and minimum z distance when trying to find an in focus image
            progress_callback (Callable): GUI widget to update progress bar
            stop_capture (Event): Event to stop capturing when possible
            is_core (bool): Is the sample a core? 
            is_vertical (bool): Only matters if is_core == True. Is the core vertically aligned?
        """
        # for loop capture
        # Change feed rate back to being slow
        self.set_feed_rate(1)
        while True and not stop_capture.is_set():
            img_num = 0

            # Targets are XYZ coordinates to jog to to capture an image.
            targets = np.vstack((targets_top, targets_bot))
            for target in targets:
                start_stack = time.time()
                if stop_capture.is_set():
                    break

                x, y, z, row, col = target[0], target[1], target[2], int(target[3]), int(target[4])

                # Jog to the origin of the core/cookie
                if img_num == 0:
                    self._gantry.jog_absolute_xyz(x, y, z)

                    # If the sample is a vertically aligned core, try to center the core in the FOV on the first 
                    if is_core and is_vertical:
                        self._gantry.block_for_jog()
                        r = 5
                        filenames = self.capture_images_multiple_x(d, n_images, self._gantry.feed_rate_z, r, self.acceleration_buffer)
                        self.recenter_core_naive(filenames, r, self._gantry.feed_rate_z)

                # Jog x and y and allow PID to handle the Z
                elif img_num == len(targets_top):
                    
                    if is_core and is_vertical:
                        self._gantry.jog_absolute_y(y)
                        self._gantry.jog_absolute_z(z)
                    else:
                        self._gantry.jog_absolute_xyz(x,y,z)

                else:
                    if is_core and is_vertical:
                        self._gantry.jog_absolute_y(y)
                    else:
                        self._gantry.jog_absolute_xy(x, y)
                    pid_lock.acquire()
                    update_z = pid_queue.get()
                    pid_lock.release()
                    z += update_z
                    log.info(f"PID update Z by {update_z} mm")
                    if update_z != 0:
                        self._gantry.jog_relative_z(update_z)

                self._gantry.block_for_jog()
                coordinates.append(self._gantry.get_xyz())
                img_filenames = self.capture_images_multiple_z(d, n_images, self._gantry.feed_rate_z, height_range, self.acceleration_buffer, row, col)
                focus_queue.put(img_filenames)
                img_num += 1

                elapsed_time = time.time() - start_stack
                progress_callback((elapsed_time, img_num, rows*cols))
            
            pid_queue.task_done() # pretty sure we don't need this 
            focus_queue.put([-1])
            break
        

    def capture_images_multiple_z(self, d: str, image_count: int, feed_rate: int, r: float, acceleration_buffer:float, row:int, col:int):
        """A method to move the camera through a Z range to allow for multiple images to be taken. This implementation is designed to reduce motion blur by taking advantage of a slow feed rate and avoiding a deceleration then sleep cycle to get an in focus image.
            This is a key component for naive image focusing. 

        Args:
            d (str): Directory of where to save frames
            image_count (int): How many images do you want to take throughout the range
            feed_rate (int): What is the feed rate of the Z-axis in mm/min
            r (float): The distance in mm between the first and last image.
            acceleration_buffer (float): Extra distance beyond the range to allow for the z-axis to reach constant velocity
            row (int): Row location of where on the cookie grid the images are in 
            col (int): Col location of where on the cookie grid the images are in 

        """
        # adding absolute jogging to start point because there is slight stochasticity between relative jogs. Resulting in drift

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
            file_location = f"{d}/frame_{row}_{col}_{i}.tiff"
            image_filenames.append(file_location)
            self.camera.save_frame(file_location)
            time.sleep(time_between_photos_s)
        
        # This might take a while so do not send the next jog until we finish the previous
        self._gantry.block_for_jog()
        # Return to original location
        # self.jog_absolute_z(z_start)
        self.jog_relative_z(-1 * bottom / 2)
        self._gantry.block_for_jog()        

        return image_filenames
    
    def capture_images_multiple_x(self, d:str, image_count: int, feed_rate: int, r: float, acceleration_buffer:float):
        """Aligning cores in the center of the field of view of the camera. Used to counteract the non zero error when jogging with the machine. Designed to run once per core. 
            This is how naive core centering would work but this could be improved with an informed approach. 
        Args:
            d (str): Directory of where to save frames
            image_count (int): How many images do you want to take throughout the range
            feed_rate (int): What is the feed rate of the Z-axis in mm/min
            r (float): The distance in mm between the first and last image.
            acceleration_buffer (float): Extra distance beyond the range to allow for the x-axis to reach constant velocity
        """
        # Assume that the machine has already jogged to the origin of the core (X0, Y0, Z0)
        # adding absolute jogging to start point because there is slight stochasticity between relative jogs. Resulting in drift
        image_filenames = []

        time_between_photos_s = r / feed_rate * 60 / image_count # mm / (mm / min) * (s / min) is the dim analysis for units of seconds
        time_zero_acceleration_s = acceleration_buffer / feed_rate * 60

        # Jog to the top of the range + acceleration buffer
        x_min = -(r / 2) - acceleration_buffer
        self.jog_relative_x(x_min, feed=feed_rate)
        self._gantry.block_for_jog()

        time.sleep(0.5)  # sleep to prevent excessive vibration

        # Jog to the x_max of the range. Begin taking photos after exiting the acceleration buffer zone
        x_max = r + (acceleration_buffer * 2)
        self.jog_relative_x(x_max, feed=feed_rate)
        # Sleep until outside of the acceleration
        time.sleep(time_zero_acceleration_s)
        
        # First photo at the x_min of the range 
        for i in range(image_count):
            file_location = f"{d}/frame_alignment_{i}.tiff"
            image_filenames.append(file_location)
            self.camera.save_frame(file_location)
            time.sleep(time_between_photos_s)
        
        # This might take a while so do not send the next jog until we finish the previous
        self._gantry.block_for_jog()
        # Return to original location
        self.jog_relative_x(-1 * (r / 2 + acceleration_buffer), feed=feed_rate)
        self._gantry.block_for_jog()        

        return image_filenames

    def recenter_core_naive(self,  filenames: list, r: float, feed:int = None):
        """After finding the best focused file from capture_images_multiple_x, center the core naively.

        Args:
            filenames (list): Filenames of all of the images captured at multiple x locations.
            r (float): The distance in mm between the first and last image.
            feed (int): Feed rate in mm/min.
            acceleration_buffer (float): Extra distance beyond the range to allow for the x-axis to reach constant velocity
        """
        focused_filename, _, _ = self.focus.best_focused_image(filenames, delete = True)
        i = filenames.index(focused_filename)
        i_middle = len(filenames) // 2 # guaranteed to be middle because n_images must be odd
        damper = 0.75
        self.jog_relative_x(((i - i_middle) / i_middle) * (r / 2) * damper, feed=feed) # max travel should be half of the range in either direction. Als
        

    def create_metadata(self, cookie: cookie.Cookie, elapsed_time: float):
        """Create metadata for the sample.

        Args:
            cookie (cookie.Cookie): Instance of the sample that was imaged
            elapsed_time (float): Time to capture 
        """
        pixels = self.camera.h_pixels * self.camera.w_pixels
        dpi = self.camera.w_pixels/cookie.image_width_mm * 25.4  
        metadata = {
            "species": cookie.species,
            "rows": cookie.rows,
            "cols": cookie.cols,
            "id1": cookie.id1,
            "id2": cookie.id2,
            "resolution_h": self.camera.h_pixels,
            "resolution_w": self.camera.w_pixels,
            "elapsed_time": elapsed_time,
            "DPI": int(dpi), # choosing ceil would also be an option but either way they introduce close to random error across all samples
            "photo_count": cookie.rows * cookie.cols,
            "image_height_mm": self.image_height_mm,
            "image_width_mm": self.image_width_mm,
            "image_crop_h": self.camera.crop_h,
            "image_crop_w": self.camera.crop_w,
            "percent_overlap": cookie.percent_overlap,
            "cookie_height_mm": cookie.height,
            "cookie_width_mm":  cookie.width,
            "camera_pixels": pixels,
            "notes": cookie.notes,
            "center": cookie.get_center_location(),
            "top_left": cookie.get_top_left_location(),
            "coordinates": cookie.coordinates,
            "background": cookie.background,
            "background_std": cookie.background_std,
            "focus_index": cookie.focus_index,
            "normalized_variance": cookie.nvar  
        }

        with open ("{}/metadata.json".format(self.directory), "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=4)

    #### JOG METHODS ####

    def jog_relative_x(self, dist: float, feed:int = None):
        """Abstraction of gantry to jog in the x direction relative to its current position.

        Args:
            dist (float): Distance in mm to jog. Negative and positive result in L/R 
            feed (int): Feed rate in mm/min.
        """
        self._gantry.jog_relative_x(dist, feed)

    def jog_relative_y(self, dist: float, feed:int = None):
        """Abstraction of gantry to jog in the Y direction relative to its current position.

        Args:
            dist (float): Distance in mm to jog. Negative and positive result in Up/Down
            feed (int): Feed rate in mm/min.
        """
        self._gantry.jog_relative_y(dist, feed)

    def jog_relative_z(self, dist: float, feed:int = None):
        """Abstraction of gantry to jog in the Z direction relative to its current position.

        Args:
            dist (float): Distance in mm to jog. Negative and positive result in Up/Down
            feed (int): Feed rate in mm/min.
        """
        self._gantry.jog_relative_z(dist, feed)
    
    def jog_absolute_x(self, pos: float, feed:int = None):
        """Abstraction of gantry to jog in the X direction to an absolute coordinate

        Args:
            pos (float): Location to jog to in coordinate system
            feed (int): Feed rate in mm/min.
        """
        self._gantry.jog_absolute_x(pos, feed)

    def jog_absolute_y(self, pos: float, feed:int = None):
        """Abstraction of gantry to jog in the Y direction to an absolute coordinate

        Args:
            pos (float): Location to jog to in coordinate system
            feed (int): Feed rate in mm/min.
        """
        self._gantry.jog_absolute_y(pos, feed)

    def jog_absolute_z(self, pos: float, feed:int = None):
        """Abstraction of gantry to jog in the Z direction to an absolute coordinate

        Args:
            pos (float): Location to jog to in coordinate system
            feed (int): Feed rate in mm/min.
        """
        self._gantry.jog_absolute_z(pos, feed)

    def jog_absolute_xy(self, x: float, y: float, feed:int = None):
        """Abstraction of gantry to jog in the X and Y direction to an absolute coordinate. Executes both at the same time

        Args:
            pos (float): Location to jog to in coordinate system
            feed (int): Feed rate in mm/min.
        """
        self._gantry.jog_absolute_xy(x, y, feed)

    def jog_absolute_xyz(self, x: float, y: float, z: float, feed:int = None):
        """Abstraction of gantry to jog in the X,Y,Z direction to an absolute coordinate. Executes all simultaneously

        Args:
            pos (float): Location to jog to in coordinate system
            feed (int): Feed rate in mm/min.
        """
        self._gantry.jog_absolute_xyz(x, y, z, feed)

    def set_feed_rate(self, mode: int):
        """Setting feed rate between fast and slow

        Args:
            mode (int): Slow mode is 1, fast mode is 2
        """
        # Slow mode
        if mode == 1:
            self._gantry.feed_rate_xy = self.slow_feed_rate_xy
            self._gantry.feed_rate_z = self.slow_feed_rate_z
        # Fast mode
        if mode == 2:
            self._gantry.feed_rate_xy = self.fast_feed_rate_xy
            self._gantry.feed_rate_z = self.fast_feed_rate_z

    def navigate_to_cookie_tl(self, cookie: cookie.Cookie):
        """Navigate to the to the top left of a cookie

        Args:
            cookie (cookie.Cookie): Instance of sample
        """
        x, y, z = cookie.get_top_left_location()
        self.jog_absolute_xyz(x, y, z)

        log.info("Navigating to {}, X{}Y{}Z{}".format(cookie.species, x, y, z))
        # Wait until we get to the cookie location
        self._gantry.block_for_jog()

    def traverse_cookie_boundary(self, cookie_width: float, cookie_height: float):
        """Traverse the borders of the stitched field of view for sample setup purposes.

        Args:
            cookie_width (float): Width of the sample
            cookie_height (float): Height of the sample
        """
        
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

    def cb_capture_image(self, name: str = None):
        """Capture an image

        Args:
            name (str, optional): Name for the file. Defaults to None.

        Returns:
            _type_: Returns the name of the file, helpful if name is default
        """
        if name is None:
            name = "{}/image_{}.tiff".format(self.directory, datetime.now().strftime("%H_%M_%S_%f"))
        self.camera.save_frame(name)
        log.info("Saving {}".format(name))
        return name
    
    #### COOKIE METHODS ####

    def add_cookie_sample(self, width: float, height: float, overlap: int, species: str, id1: str, id2: str, notes: str):
        """Callback for GUI to add a sample

        Args:
            width (float): Width of sample 
            height (float): Height of sample 
            overlap (int): Percent overlap 
            species (str): Species ID 
            id1 (str): ID1 for sample
            id2 (str): ID2 for sample
            notes (str): Notes for sample
        """
        time.sleep(1) # guarantee the position monitor is updated
        center_x, center_y, center_z = self._gantry.get_xyz()
        print("CENTER")
        print(center_x, center_y, center_z)
        if overlap == '':
            overlap = 50
        if species == '':
            species = "na"
        if id1 == '':
            id1 = "na"
        if id2 == '':
            id2 = "na"

        #path_name = self.cb_capture_image()
        ck = cookie.Cookie(width, height, species, id1, id2, notes, self.image_width_mm, self.image_height_mm, overlap, center_x, center_y, center_z)
        self.cookies.append(ck)

    def get_cookies(self):
        """List cookies

        Returns:
            list[cookie.Cookies]: List of the cookies for GUI usage
        """
        return self.cookies
    
    def set_cookies(self, cookies: list[cookie.Cookie]):
        """Set the cookies attribute

        Args:
            cookies (list[cookie.Cookie]): A list of cookie.Cookies
        """
        self.cookies=cookies

   #### GANTRY METHODS ####

    def serial_connect(self):
        """Connect to the gantry via USB serial
        """
        self._gantry.serial_connect_port()

    def cb_pause_g_code(self):
        """Pause callback. Pretty sure this doesn't work right now.
        """
        self._gantry.pause()

    def cb_resume_g_code(self):
        """Resume callback. Pretty sure this doesn't work right now.
        """
        self._gantry.resume()

    def cb_homing_g_code(self):
        """Activate homing sequence to touch all limit switches.
        """
        # Move to the limit switches
        self._gantry.homing_sequence() 

        # Set the datum to work with G90 jogs 
        self._gantry.set_origin()
        
