import gantry
import focus
import sample
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
    def __init__(self, g: gantry.Gantry, c: camera.Camera, f: focus.Focus):
        """Abstraction of the controller which moves the gantry, gets information from the GUI, operates the camera, and determines when to stitch.

            g (gantry.Gantry): Gantry instance to interface with the GRBL controller.
            c (camera.Camera): Camera instance to interface with the GStreamer pipeline and camera.
            f (focus.Focus): Focus instance to capture in focus images.
        """
        #Settings for capturing images from multiple distances
        self.config = utils.load_config()
        self.n_images = self.config["controller"]["N_IMAGES_MULTIPLE_DISTANCES"] #make sure you're not going faster than the frame rate of the GStreamer feed... 
        self.height_range = self.config["controller"]["HEIGHT_RANGE_MM"]
        self.acceleration_buffer = self.config["controller"]["ACCELERATION_BUFFER_MM"]
        self.stitch_sizes = self.config["controller"]["STITCH_SIZES"]
        self.slow_feed_rate_xy = self.config["controller"]["SLOW_FEED_RATE_XY"]
        self.slow_feed_rate_z = self.config["controller"]["SLOW_FEED_RATE_Z"]
        self.fast_feed_rate_xy = self.config["controller"]["FAST_FEED_RATE_XY"]
        self.fast_feed_rate_z = self.config["controller"]["FAST_FEED_RATE_Z"]
        self.max_dpi = self.config["camera"]["MAX_DPI"]
    
        #Objects
        self.samples = []
        self._gantry = g
        self.camera = c
        self.focus = f

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
    
    def capture_sample(self, sample: sample.Sample, progress_callback: Callable, stop_capture: Event):
        """Abstraction to execute a capture sequence. This involves moving the the top left of the sample, traversing in a serpentining pattern 
        across the dimensions of the sample. At each step in the grid, multiple images are taken and only the most in focus is kept. 

        Args:
            sample (sample.Sample): Instance of a sample to be captured
            progress_callback (Callable): GUI Callback to update progress bar 
            stop_capture (Event): Event to stop capture after the current image sequence 
        """

        while not stop_capture.is_set():
            focus_queue = queue.Queue()
            pid_queue = queue.Queue()
            pid_lock = Lock()

            self.focus.set_setpoint(round(self.n_images/2))

            #set directories
            self.set_directory(sample.directory)

            start_time = time.time()

            sample.set_start_time_imaging(start_time)
            gantry_thread = Thread(target=self.capture_grid_photos, args=(sample, focus_queue, pid_queue, pid_lock, progress_callback, stop_capture))
            focus_thread = Thread(target=self.focus.find_focus, args=(sample, focus_queue, pid_queue, pid_lock))
            gantry_thread.start()
            focus_thread.start()
            
            gantry_thread.join()	
            focus_queue.join()    	
            focus_thread.join()

            end_time = time.time()
            sample.set_end_time_imaging(end_time)
            sample.to_json()
            break

    def capture_all_samples(self, progress_callback: Callable, stop_capture: Event):
        """Callable for the GUI to iterate through all samples. For multiple sample capture.

        Args:
            progress_callback (Callable): GUI widget to update progress bar
            stop_capture (Event): Event to stop capture as soon as possible
        """
        while not stop_capture.is_set():
            for i in range(len(self.samples)):
                sample = self.samples.pop(-1)
                width_est_pixels = sample.width / sample.image_width_mm * self.camera.w_pixels 
                height_est_pixels = sample.height / sample.image_height_mm * self.camera.h_pixels
                max_filesize_est = width_est_pixels * height_est_pixels * 3 / 10e6 # megabytes
                log.info("MAX FILE SIZE ESTIMATE {} MB".format(round(max_filesize_est, 2)))
                progress_callback((True, True, "{}_{}_{}".format(sample.species, sample.id1, sample.id2)))

                self.capture_sample(sample, progress_callback, stop_capture)
                
                # Only stitch if the capture complete successfully
                if not stop_capture.is_set():
                    print('stitching frames')
                    self.stitch_frames(sample)
                if len(self.samples) == 0:
                    stop_capture.set()

            return

    def stitch_frames(self, sample: sample.Sample):
        """Stitch together frames into a mosaic. Not perfect yet as retrofitting Stitch2d is slightly cumbersome. If running into stitching issues, such as 'Killed' 
        or OOM, please try stitching using a more power computer with 16 GB of rame or something. This is a decently high priority to fix.

        Args:
            sample (str): sample.Sample which is being stitched.. 
        """

        for size in self.stitch_sizes:
            st = stitcher.Stitcher(sample) 
            #st.stitch(resize=size)
            try:
                sample.set_dpi(size, self.max_dpi)
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
    
    def capture_grid_photos(self, sample: sample.Sample, focus_queue: queue.Queue, pid_queue: queue.Queue, pid_lock, progress_callback: Callable, stop_capture: Event):
        """Command to traverse the sample and capture an image at each location. 

        Args:
            sample(sample.Sample): Sample object which contains all the relevant sample information.
            focus_queue (queue.Queue): Queue to have images added to for the focus thread to parse which is the most in focus.
            pid_queue (queue.Queue): Queue to determine if the z height needs to be adjusted to stay in focus.
            pid_lock (_type_): Lock to prevent race conditions
            progress_callback (Callable): GUI widget to update progress bar
            stop_capture (Event): Event to stop capturing when possible
        """
        # for loop capture
        # Change feed rate back to being slow
        self.set_feed_rate(1)
        while True and not stop_capture.is_set():
            img_num = 0

            # Targets are XYZ coordinates to jog to to capture an image.
            targets = np.vstack((sample.targets_top, sample.targets_bot))
            for target in targets:
                self._gantry.block_for_jog()
                start_stack = time.time()
                if stop_capture.is_set():
                    break

                x, y, z, row, col = target[0], target[1], target[2], int(target[3]), int(target[4])

                # Jog to the origin of the sample
                if img_num == 0:
                    self._gantry.jog_absolute_xyz(x, y, z)

                    # If the sample is a vertically aligned core, try to center the core in the FOV on the first 
                    if sample.is_core and sample.is_vertical:
                        log.info("Core centering procedure start.")
                        self._gantry.block_for_jog()
                        r = self.config["controller"]["CORE_CENTERING_RANGE"] #5
                        n_images_centering = self.config["controller"]["N_IMAGES_CORE_CENTERING"]
                        filenames = self.capture_images_multiple_x(sample.directory, n_images_centering, self._gantry.feed_rate_z, r, self.acceleration_buffer)
                        self.recenter_core_naive(filenames, r, self._gantry.feed_rate_z)
                # Jog x and y and allow PID to handle the Z
                elif img_num == len(sample.targets_top):
                    
                    if sample.is_core and sample.is_vertical:
                        self._gantry.jog_absolute_y(y)
                        self._gantry.jog_absolute_z(z)
                    else:
                        self._gantry.jog_absolute_xyz(x,y,z)
                else:
                    if sample.is_core and sample.is_vertical:
                        self._gantry.jog_absolute_y(y)
                    else:
                        self._gantry.jog_absolute_xy(x, y)
                    # pid_lock.acquire()
                    update_z = pid_queue.get()
                    # pid_lock.release()
                    z += update_z
                    log.info(f"PID update Z by {update_z} mm")
                    if update_z != 0:
                        self._gantry.jog_relative_z(update_z)


                sample.coordinates.append(self._gantry.get_xyz())
                img_filenames = self.capture_images_multiple_z(sample.directory, self.n_images, self._gantry.feed_rate_z, self.height_range, self.acceleration_buffer, row, col)
                focus_queue.put(img_filenames)
                img_num += 1

                elapsed_time = time.time() - start_stack
                progress_callback((elapsed_time, img_num, sample.rows*sample.cols))
            
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
            row (int): Row location of where on the sample grid the images are in 
            col (int): Col location of where on the sample grid the images are in 

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
        log.info("Jog to original location.")
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
        d = ((i - i_middle) / i_middle) * (r / 2) * damper
        self.jog_relative_x(d, feed=feed) # max travel should be half of the range in either direction. Als
        log.info("Jog {} mm to recenter vertical core. i: {}, i_middle: {}".format(d, i, i_middle))

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
    
    ############## testing ###############

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

    def navigate_to_sample_tl(self, sample: sample.Sample):
        """Navigate to the to the top left of a sample

        Args:
            sample (sample.Sample): Instance of sample
        """
        x, y, z = sample.get_top_left_location()
        self.jog_absolute_xyz(x, y, z)

        log.info("Navigating to {}, X{}Y{}Z{}".format(sample.species, x, y, z))
        # Wait until we get to the sample location
        self._gantry.block_for_jog()

    def traverse_sample_boundary(self, sample_width: float, sample_height: float):
        """Traverse the borders of the stitched field of view for sample setup purposes.

        Args:
            sample_width (float): Width of the sample
            sample_height (float): Height of the sample
        """
        
        try: 
            x, y, z = self._gantry.get_xyz()

            l_x = x - (sample_width / 2)
            r_x = x + (sample_width / 2)
            b_y = y - (sample_height/ 2)
            t_y = y + (sample_height / 2)

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
            log.info("sample not defined")


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
    
    #### SAMPLE METHODS ####

    def add_sample(self, width: float, height: float, overlap: int, species: str, id1: str, id2: str, notes: str, is_core: bool):
        """Callback for GUI to add a sample

        Args:
            width (float): Width of sample 
            height (float): Height of sample 
            overlap (int): Percent overlap 
            species (str): Species ID 
            id1 (str): ID1 for sample
            id2 (str): ID2 for sample
            notes (str): Notes for sample
            is_core (bool): Is the sample a core? 
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
        ck = sample.Sample(width, height, species, id1, id2, notes, self.image_width_mm, self.image_height_mm, self.camera.w_pixels, self.camera.h_pixels, is_core, percent_overlap=overlap, x=center_x, y=center_y, z=center_z)
        self.samples.append(ck)

    def get_samples(self):
        """List samples

        Returns:
            list[sample.Sample]: List of the samples for GUI usage
        """
        return self.samples
    
    def set_samples(self, samples: list[sample.Sample]):
        """Set the samples attribute

        Args:
            samples (list[sample.Sample]): A list of sample.Sample
        """
        self.samples=samples

   #### GANTRY METHODS ####
    def send_gcode_cmd(self, cmd:str) -> list:
       self._gantry._send_command(cmd)

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
        
