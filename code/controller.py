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


class Controller:
    def __init__(self, image_width_mm: float, image_height_mm: float):
        """Abstraction of the controller which moves the gantry, gets information from the GUI, operates the camera, and determines when to stitch.

        Args:
            image_width_mm (float): Initial image width
            image_height_mm (float): Initial image height
        """
        #Settings for capturing images from multiple distances
        self.n_images = 9 #make sure you're not going faster than the frame rate of the GStreamer feed... 
        self.height_range = 1
        
        #Objects
        self.cookies = []
        self._gantry = gantry.Gantry()
        self.camera = camera.Camera()
        self.focus = focus.Focus(delete_flag=True, setpoint=round(self.n_images / 2))

        #attributes
        self.image_height_mm = image_height_mm
        self.image_width_mm = image_width_mm
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

            _, _, z = cookie.get_center_location()
        
            gantry_thread = Thread(target=self.capture_grid_photos, args=(cookie.coordinates, cookie.directory, focus_queue, pid_queue, pid_lock, cookie.rows, cookie.cols, cookie.y_step_size, cookie.x_step_size, z, self.n_images, self.height_range, progress_callback, stop_capture))
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
                log.info("MAX FILE SIZE ESTIMATE {}".format(max_filesize_est))
                progress_callback((True, True, "{}_{}_{}".format(cookie.species, cookie.id1, cookie.id2)))
                self.navigate_to_cookie_tl(cookie)
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
        sizes = [0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
        for size in sizes:
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
    
    def capture_grid_photos(self, coordinates: list, d: Path, focus_queue: queue.Queue, pid_queue: queue.Queue, pid_lock, rows: int, cols: int, y_dist: float, x_dist: float, z_start: float, n_images: int, height_range: float, progress_callback: Callable, stop_capture: Event):
        """Command to traverse the sample and capture an image at each location. 

        Args:
            coordinates (list): Container for holding the coordinates of where each image was taken. Useful for debugging.
            d (Path): Directory to save.
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
        """
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
                    
                    current_col = None
                    if row % 2 == 1:
                        current_col = cols - col - 1
                        coordinates[row][current_col] = self._gantry.get_xyz()
                        imgs = self.capture_images_multiple_distances(d, n_images, self._gantry.feed_rate_z, height_range, 0.2, row, current_col, z_start)
                        pid_lock.acquire()
                        self.jog_relative_x(-x_dist)
                        pid_lock.release()
                    # Even rows go right
                    else:
                        current_col = col
                        coordinates[row][current_col] = self._gantry.get_xyz()
                        imgs = self.capture_images_multiple_distances(d, n_images, self._gantry.feed_rate_z, height_range, 0.2, row, current_col, z_start)
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
                    current_col = 0
                    coordinates[row][current_col] = self._gantry.get_xyz()
                    imgs = self.capture_images_multiple_distances(d, n_images, self._gantry.feed_rate_z, height_range, 0.2, row, current_col, z_start)

                else:
                    # imgs = self.capture_images_multiple_distances(0.05, z_steps, row, cols - 1)
                    current_col = cols - 1
                    coordinates[row][current_col] = self._gantry.get_xyz()

                    imgs = self.capture_images_multiple_distances(d, n_images, self._gantry.feed_rate_z, height_range, 0.2, row, current_col, z_start)
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

    def capture_images_multiple_distances(self, d: str, image_count: int, feed_rate: int, r: float, acceleration_buffer:float, row:int, col:int, z_start:float):
        """A method to move the camera through a Z range to allow for multiple images to be taken. This implementation is designed to reduce motion blur by taking advantage of a slow feed rate and avoiding a deceleration then sleep cycle to get an in focus image.

        Args:
            d (str): Directory of where to save frames
            image_count (int): How many images do you want to take throughout the range
            feed_rate (int): What is the feed rate of the Z-axis in mm/min
            r (float): The distance in mm between the first and last image.
            acceleration_buffer (float): Extra distance beyond the range to allow for the z-axis to reach constant velocity
            row (int): Row location of where on the cookie grid the images are in 
            col (int): Col location of where on the cookie grid the images are in 
            z_start (float): Starting z location as it's a bit more accurate to jog to a specific coordinate than to use relative position jogging

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
            file_location = f"{d}/frame_{row}_{col}_{i}.tiff"
            image_filenames.append(file_location)
            self.camera.save_frame(file_location)
            time.sleep(time_between_photos_s)
        
        # This might take a while so do not send the next jog until we finish the previous
        self._gantry.block_for_jog()
        # Return to original location
        self.jog_absolute_z(z_start)
        self._gantry.block_for_jog()        

        return image_filenames
    
    def create_metadata(self, cookie: cookie.Cookie, elapsed_time: float):
        """Create metadata for the sample.

        Args:
            cookie (cookie.Cookie): Instance of the sample that was imaged
            elapsed_time (float): Time to capture 
        """
        pixels = self.camera.h_pixels * self.camera.w_pixels
        dpi = self.camera.w_pixels/self.image_width_mm * 25.4  
        metadata = {
            "species": cookie.species,
            "rows": cookie.rows,
            "cols": cookie.cols,
            "id1": cookie.id1,
            "id2": cookie.id2,
            "resolution_h": self.camera.h_pixels,
            "resolution_w": self.camera.w_pixels,
            "elapsed_time": elapsed_time,
            "DPI": round(dpi,2),
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
            "coordinates": cookie.coordinates.tolist(),
            "background": cookie.background.tolist(),
            "background_std": cookie.background_std.tolist(),
            "focus_index": cookie.focus_index.tolist(),
            "normalized_variance": cookie.nvar.tolist()  
        }

        with open ("{}/metadata.json".format(self.directory), "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=4)

    #### JOG METHODS ####

    def jog_relative_x(self, dist: float):
        """Abstraction of gantry to jog in the x direction relative to its current position.

        Args:
            dist (float): Distance in mm to jog. Negative and positive result in L/R 
        """
        self._gantry.jog_relative_x(dist)

    def jog_relative_y(self, dist: float):
        """Abstraction of gantry to jog in the Y direction relative to its current position.

        Args:
            dist (float): Distance in mm to jog. Negative and positive result in Up/Down
        """
        self._gantry.jog_relative_y(dist)

    def jog_relative_z(self, dist: float):
        """Abstraction of gantry to jog in the Z direction relative to its current position.

        Args:
            dist (float): Distance in mm to jog. Negative and positive result in Up/Down
        """
        self._gantry.jog_relative_z(dist)
    
    def jog_absolute_x(self, pos: float):
        """Abstraction of gantry to jog in the X direction to an absolute coordinate

        Args:
            pos (float): Location to jog to in coordinate system
        """
        self._gantry.jog_absolute_x(pos)

    def jog_absolute_y(self, pos: float):
        """Abstraction of gantry to jog in the Y direction to an absolute coordinate

        Args:
            pos (float): Location to jog to in coordinate system
        """
        self._gantry.jog_absolute_y(pos)

    def jog_absolute_z(self, pos: float):
        """Abstraction of gantry to jog in the Z direction to an absolute coordinate

        Args:
            pos (float): Location to jog to in coordinate system
        """
        self._gantry.jog_absolute_z(pos)

    def jog_absolute_xy(self, x: float, y: float):
        """Abstraction of gantry to jog in the X and Y direction to an absolute coordinate. Executes both at the same time

        Args:
            pos (float): Location to jog to in coordinate system
        """
        self._gantry.jog_absolute_xy(x, y)

    def jog_absolute_xyz(self, x: float, y: float, z: float):
        """Abstraction of gantry to jog in the X,Y,Z direction to an absolute coordinate. Executes all simultaneously

        Args:
            pos (float): Location to jog to in coordinate system
        """
        self._gantry.jog_absolute_xyz(x, y, z)

    def set_feed_rate(self, mode: int):
        """Setting feed rate between fast and slow

        Args:
            mode (int): Slow mode is 1, fast mode is 2
        """
        # Slow mode
        if mode == 1:
            self._gantry.feed_rate_xy = 300
            self._gantry.feed_rate_z = 20
        # Fast mode
        if mode == 2:
            self._gantry.feed_rate_xy = 1250
            self._gantry.feed_rate_z = 150

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
        center_x, center_y, center_z = self._gantry.get_xyz()

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
        
