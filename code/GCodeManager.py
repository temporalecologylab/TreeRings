import logging as log
import math
import serial
import time
from threading import Lock, Thread
import cv2
import focus_stack
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GObject, GLib

log.basicConfig(format='%(process)d-%(levelname)s-%(message)s', level=log.INFO)

class CoreSample:
    pass


class VideoSaver:
    def __init__(self):
        Gst.init(None)
        # Create the pipeline with both display and save frame functionality
        self.pipeline = Gst.parse_launch(
            "nvarguscamerasrc ! video/x-raw(memory:NVMM),width=3840,height=2160,framerate=30/1 ! nvvideoconvert flip-method=2 ! tee name=t "
            "t. ! queue ! autovideosink "
            "t. ! queue ! nvjpegenc ! multifilesink name=sink"
        )
        self.filesink = self.pipeline.get_by_name("sink")
        self.filesink.set_property("location", "/dev/null")
        self.filesink.set_property("next-file", 4)  # 4 is the value for "max-size"
        self.filesink.set_property("max-file-size", 1)  # We only want one file

    def start_pipeline(self):
        self.pipeline.set_state(Gst.State.PLAYING)
        print("Pipeline started")

    def stop_pipeline(self):
        self.pipeline.set_state(Gst.State.NULL)
        print("Pipeline stopped")

    def save_frame(self, path):
        self.filesink.set_property("location", path)
        self.filesink.send_event(Gst.Event.new_eos())

    def reset_sink(self):
        # Reset the filesink to not save any more frames
        self.filesink.set_property("location", "/dev/null")
        self.pipeline.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH, 0)
        print("Sink reset")


class CookieSample:
    def __init__(self, cookie_width_mm: int, cookie_height_mm: int, percent_overlap:int = 20):
        self.width = cookie_width_mm
        self.height = cookie_height_mm
        self.percent_overlap = percent_overlap
        self.start_point = (None, None)

    def set_location(self, top_left: tuple[int, int]):
        self.start_point = top_left

class MachineControl:
    def __init__(self, image_width_mm: int, image_height_mm: int, serial_port = "/dev/ttyUSB0", x_soft_limit = 700, y_soft_limit = 700, z_soft_limit = 200):
        self._serial_port = serial_port # windows should be a "COM[X]" port which will vary per device
        
        # image dimensions TODO: create calibration sequence to automatically change this based on measuring ArUco marker
        self.image_width_mm = image_width_mm
        self.image_height_mm = image_height_mm

        # distance the machine can travel without breaking itself
        self._x_soft_limit = x_soft_limit 
        self._y_soft_limit = y_soft_limit
        self._z_soft_limit = z_soft_limit 

        # machine settings
        self.feed_rate_z = 10
        self.feed_rate_xy = 300 

        self.feed_rate_fast_z = 100
        self.feed_rate_fast_xy = 500

        # sample information
        self.cookie_samples = []
        self.core_samples = []

        # mutex for taking images
        self.mutex_camera = Lock()
        
        self.stop_glib = False
        self.glib_thread = Thread(target=self.run_glib)
        self.start_camera_filesave()

    def gstreamer_pipeline_filesave_tee(
        self,
        sensor_id=0,
        capture_width=3840,
        capture_height=2160,
        display_width=640,
        display_height=480,
        framerate=30,
        flip_method=1,
    ):
        return (
            "nvarguscamerasrc ! nvvideoconvert ! tee name=t "
            "t. ! queue ! autovideosink "
            "t. ! queue ! nvjpegenc ! multifilesink name=sink"
            )
        

    def gstreamer_pipeline(
        self,
        sensor_id=0,
        capture_width=3840,
        capture_height=2160,
        display_width=640,
        display_height=480,
        framerate=30,
        flip_method=1,
    ):
        return (
            "nvarguscamerasrc sensor-id={} ! "
            "video/x-raw(memory:NVMM), width=(int){}, height=(int){}, framerate=(fraction){}/1 ! "
            "nvvidconv flip-method={} ! "
            "video/x-raw, width=(int){}, height=(int){}, format=(string)BGRx ! "
            "videoconvert ! "
            "video/x-raw, format=(string)BGR ! appsink".format(
                sensor_id,
                capture_width,
                capture_height,
                framerate,
                flip_method,
                display_width,
                display_height,
            )
        )

    def start_camera_filesave(self):

        log.info("Starting pipeline \n")
        
        self.video_saver = VideoSaver()
        self.video_saver.start_pipeline()

        self.glib_thread.start()
    
    def end_camera_filesave(self):
        self.video_saver.stop_pipeline()
        self.stop_glib = True
        self.glib_thread.join()
    

    def run_glib(self):
        loop = GLib.MainLoop()
        GLib.timeout_add_seconds(1, not self.stop_glib)
        try:
            loop.run()
        except KeyboardInterrupt:
            self.stop_glib = True
            loop.quit()

    def reset_sink(self):
        # Reset the filesink to not save any more frames
        self.filesink.set_property("location", "/dev/null")
        self.pipeline.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH, 0)
        print("Sink reset")

    def save_image(self, path):
        
        # Generate a unique filename with a timestamp
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        file_location = f"frame_{timestamp}.jpg"
        
        self.video_saver.save_frame(path)

    def display_stream(self):
        self.tr = Thread(target = self._display_stream, daemon=True)
        self.tr.start()

    def _display_stream(self):
        REFRESH_RATE = 15 #hz
        window_title = "HQ Camera"
        window_handle = cv2.namedWindow(window_title, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_title, 640, 480)
        if self.video_stream.isOpened():

            try:
                while True:            
                    frame = self.capture_image()

                    cv2.imshow(window_title, frame)
                    
                    keyCode = cv2.waitKey(int(1000 / 15)) & 0xFF
                    # Stop the program on the ESC key or 'q'
                    if keyCode == 27 or keyCode == ord('q'):
                        break

            finally:
                cv2.destroyAllWindows()

    def capture_image(self):
        self.mutex_camera.acquire(blocking=True)
        _, frame = self.video_stream.read()
        self.mutex_camera.release()
        return frame

    def add_cookie_sample(self, cookie_width_mm: int, cookie_height_mm: int, percent_overlap: int = 20) -> None:
        cookie = CookieSample(cookie_width_mm, cookie_height_mm, percent_overlap = percent_overlap)
        self.cookie_samples.append(cookie)

    def add_core_sample(self, core: CoreSample) -> None:
        self.core_samples.append(core) 

    def set_feed_rate_xy(self, feed_rate):
        self.feed_rate_xy = feed_rate

    def set_feed_rate_z(self, feed_rate):
        self.feed_rate_z = feed_rate

    def send_command(self, cmd) -> str:
        log.info("Sending {}".format(cmd))
        self.s.write(str.encode("{}\n".format(cmd))) # Send g-code block to grbl
        grbl_out = self.s.readline() # Wait for grbl response with carriage return
        self.log_serial_out(grbl_out)
        return grbl_out

    def jog_x(self, dist) -> None:
        '''
        Jog a distance (mm) from the current location in the x plane, NOT to an absolute position. 
        +dist moves to the +x
        -dist moves to the -x
        '''
        cmd = "$J=G91 G21 X{} F{}".format(dist, self.feed_rate_xy)
        self.send_command(cmd)

    def jog_y(self, dist) -> None:
        '''
        Jog a distance (mm) from the current location in the y plane, NOT to an absolute position. 
        +dist moves to the +y
        -dist moves to the -y
        '''
        cmd = "$J=G91 G21 Y{} F{}".format(dist, self.feed_rate_xy)
        self.send_command(cmd)

    def jog_z(self, dist) -> None:
        '''
        Jog a distance (mm) from the current location in the z plane, NOT to an absolute position. 
        +dist moves to the +z
        -dist moves to the -z
        '''
        cmd = "$J=G91 G21 Z{} F{}".format(dist, self.feed_rate_z)
        self.send_command(cmd)
        
    def jog_fast_x(self, dist) -> None:
        '''
        Jog a distance (mm) from the current location in the x plane, NOT to an absolute position. 
        +dist moves to the +x
        -dist moves to the -x

        '''
        cmd = "$J=G91 G21 X{} F{}".format(dist, self.feed_rate_fast_xy)
        self.send_command(cmd)

    def jog_fast_y(self, dist) -> None:
        '''
        Jog a distance (mm) from the current location in the y plane, NOT to an absolute position. 

        +dist moves to the +y
        -dist moves to the -y
        '''
        cmd = "$J=G91 G21 Y{} F{}".format(dist, self.feed_rate_fast_xy)
        self.send_command(cmd)

    def jog_fast_z(self, dist) -> None:

        '''

        Jog a distance (mm) from the current location in the z plane, NOT to an absolute position. 
        +dist moves to the +z
        -dist moves to the -z
        '''
        cmd = "$J=G91 G21 Z{} F{}".format(dist, self.feed_rate_fast_z)
        self.send_command(cmd)


    def stack_sequence(self, step_size_mm: float, image_count_odd: int, col, row, directory, pause = 1):
        images = []
        dist = 0 #distance from zero 

        if image_count_odd // 2 == 0:
            return "MUST BE ODD"
        
        z_offset = round(math.floor(image_count_odd / 2) * step_size_mm, 3)

        # go to the bottom of the range 
        self.jog_z(-z_offset)
        
        #take first photo in stack
        file_location = f"{directory}/frame_{col}_{row}_{0}.jpg"
        log.info("Stack image {}".format(file_location))
        self.save_image(file_location)
        time.sleep(pause)
        
        # move upwards by a step, take a photo, then repeat
        for i in range(1, image_count_odd):
            #timestamp = time.strftime("%Y%m%d_%H%M%S")
            
            self.jog_z(step_size_mm)
            time.sleep(pause)
            file_location = f"{directory}/frame_{col}_{row}_{i}.jpg"
            log.info("Stack image {}".format(file_location))
            self.save_image(file_location)
        
        # self.save_frame()
        # return to original position
        self.jog_z(-z_offset)
        time.sleep(pause)

    
    def jog_cancel(self) -> None:
        """Immediately cancels the current jog state by a feed hold and
        automatically flushing any remaining jog commands in the buffer.
        Command is ignored, if not in a JOG state or if jog cancel is already
        invoked and in-process.
        """
        cmd = "\x85"
        self.send_command(cmd)
    
    def pause(self) -> None:
        cmd = "M0"
        self.send_command(cmd)

    def resume(self) -> None:
        cmd = "~"
        self.send_command(cmd)

    def homing_sequence(self) -> None:
        cmd = "$H"
        self.send_command(cmd)
        self.query_state()

    def query_state(self) -> None:
        """Query the state of the machine. Updates the attribute if the machine is connected
        """
        cmd = "?"
        res = self.send_command(cmd)
        res_str = res.decode("utf-8")
        if res_str[-2:] == "ok":
            self._connected = True
        else:
            self._connected = False

    def is_connected(self):
        if self._connected:
            return True
        else:
            return False
        
    def log_serial_out(self, s_out):
        log.info(' : ' + str(s_out.strip()))

    def serial_connect_port(self) -> None:
        log.info("Connecting to GRBL via serial")
        self.s = serial.Serial(self._serial_port, 115200) # WILL NEED TO CHANGE THIS PER DEVICE / OS
        self.s.write(b"\r\n\r\n")
        time.sleep(2)# Wait for grbl to initialize 
        # Wake up grbl
        grbl_out = self.s.readline() # Wait for grbl response with carriage return
        grbl_out_str = grbl_out.decode("utf-8")

        if grbl_out_str.strip() == "ok":
            self._connected = True
        else:
            self._connected = False

        self.log_serial_out(grbl_out)
        self.s.flushInput()  # Flush startup t
        log.info("Input flushed")

    def serial_disconnect_port(self):
    	#TODO: somehow make it so we dont have to reset blackbox?
        self.s.close()
    
    def enable_soft_limits(self):
        cmd = "$20 1"
        self.send_command(cmd)
    
    def disable_soft_limits(self):
        cmd = "$20 0"
        self.send_command(cmd)

    def send_serpentine(self, img_pipeline, g_code, directory, pause = 2, z_steps = 7):
        log.info("Starting serpentine")
        for i in range(0, len(g_code)):
            for j in range(0, len(g_code[i])):
                #self.stack_sequence(0.1, z_steps, i, j, directory, pause=1)
                if i % 2 == 1:
                    col = len(g_code[i]) - j - 1
                    self.save_image("{}/frame_{}_{}.jpg".format(directory, i, col))
                else:
                    self.save_image("{}/frame_{}_{}.jpg".format(directory, i, j))
                log.info("Stack {}, {} finished of {}".format(i,j, len(g_code) * len(g_code[i])))
                log.info("Traversing")
                self.send_command(g_code[i][j])
                time.sleep(pause)
                img_pipeline.put([i,j,z_steps])

        self.save_image("{}/frame_trash.jpg".format(directory))
        img_pipeline.put([-1,-1,-1])

    def focus_thread(self, img_pipeline, directory):
        while True:
            args = img_pipeline.get()
            log.info(args)
            i = args[0]
            j = args[1]
            z = args[2]
            if i == -1:
                img_pipeline.task_done()
                break
            for k in range (0, z):
                imgs = []
                imgs.append(cv2.imread("/{}/frame_{}_{}_{}.jpg".format(directory, i, j, k)))
                log.info("calling focus method")
                focused_image = self.best_focused_image(imgs)
                cv2.imwrite("/{}/focused_images/focused_{}_{}.jpg".format(directory,i,j), focused_image)
            img_pipeline.task_done()
        
    def best_focused_image(self, images):
        best_image = []
        best_lap = 0.0

        for image in images:
            lap = self.compute_laplacian(image)
            if lap.var() > best_lap:
                best_lap = lap.var()
                best_image = image

        return best_image
    
    def compute_laplacian(self,image):

        # odd numbers only, can be tuned
        kernel_size = 5         # Size of the laplacian window
        blur_size = 5           # How big of a kernel to use for the gaussian blur

        blurred = cv2.GaussianBlur(image, (blur_size,blur_size), 0)
        return cv2.Laplacian(blurred, cv2.CV_64F, ksize=kernel_size)            

    def generate_serpentine(self, cookie: CookieSample) -> list[list[str]]:
        # TODO: make this work for multiple cookies... this is going to be interesting

        g_code = []

        # More than 0.00 precision is unrealistic with the machinery
        overlap_x = round(self.image_width_mm * cookie.percent_overlap / 100, 3)
        overlap_y = round(self.image_height_mm * cookie.percent_overlap / 100, 3)

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

        total_images = x_steps * y_steps
        
        
        log.info("Creating G-Code for {} serpentine images".format(total_images))
        
        # begin serpentine logic
        #g_code[0].append("$J=G91 G21 X{} F{}".format(x_step_size, self.feed_rate_xy)) # set and forget feed

        i = 0
        for y_step in range(0, y_steps):
            g_code_i = []
            
            x = round(x_step_size, 2)
            
            # Don't go further down after the final row is finished
            if y_step != y_steps - 1 & y_step != 0:
                g_code_i.append(f"$J=G91 G21 Y-{y} F{self.feed_rate_xy}")
            else:
                g_code_i.append(f"$J=G91 G21 X{x} F{self.feed_rate_xy}")
                
            
            # Move in X-direction with overlap
            for _ in range(0, x_steps - 1): # -1 because the y movement counts as the first image in the new row
                g_code_i.append(f"$J=G91 G21 X{x} F{self.feed_rate_xy}")

            # Move down one step in the +Y-direction with overlap
            y = round(y_step_size, 2)
		              
            g_code.append(g_code_i)
            x_step_size *= -1 # switch X directions
            i += 1

        # End program
        # g_code.append("M2")
        log.info(g_code)
        return g_code
# class GCodeManager:
#     def __init__(self, cookie_width_mm: int, cookie_height_mm: int, image_width_mm: int, image_height_mm: int, feed_rate: int, overlap_percentage: int, start_point: tuple[int, int]=(0, 0)) -> None:
#         self.cookie_width_mm = cookie_width_mm
#         self.cookie_height_mm = cookie_height_mm
#         self.image_width_mm = image_width_mm
#         self.image_height_mm = image_height_mm
#         self.feed_rate = feed_rate # mm/min
#         self.overlap_percentage = overlap_percentage
#         self.start_point = start_point
#         self.max_z = 100 # mm
#         self.g_code = self.generate_serpentine()
#         self._n_line = 0 # current line of g_code 

#         # starts at zero if homed, #TODO: get feedback from GCODE
#         self.x = 0
#         self.y = 0
#         self.z = 0

#     def generate_serpentine(self) -> list[str]:
#         g_code = []

#         # More than 0.00 precision is unrealistic with the machinery
#         overlap_x = round(self.image_width_mm * self.overlap_percentage / 100, 2)
#         overlap_y = round(self.image_height_mm * self.overlap_percentage / 100, 2)


#         # TODO: add logic / user input / something to move z to be in focus
#         x_step_size = cookie.width - overlap_x
#         y_step_size = cookie.height - overlap_y 


#         x_steps = math.ceil(self.cookie_width_mm / x_step_size)
#         y_steps = math.ceil(self.cookie_height_mm / y_step_size)
#         total_images = x_steps * y_steps
        
        
#         log.info("Creating G-Code for {} serpentine images".format(total_images))
        
#         # begin serpentine logic
#         g_code.append("$J=G91 G21 X{} F{}".format(x_step_size, self.feed_rate)) # set and forget feed

#         for y_step in range(0, y_steps):

#             # Move in X-direction with overlap
#             for _ in range(0, x_steps - 1): # -1 because the y movement counts as the first image in the new row
#                 x = round(x_step_size, 2)
#                 g_code.append(f"$J=G91 G21 X{x} F{self.feed_rate}")

#             # Move down one step in the +Y-direction with overlap
#             y = round(y_step_size, 2)

#             # Don't go further down after the final row is finished
#             if y_step != y_steps - 1:
#                 g_code.append(f"$J=G91 G21 Y-{y} F{self.feed_rate}")

#             x_step_size *= -1 # switch X directions

#         # End program
#         g_code.append("M2")

#         return g_code

#     def serial_connect_port(self, port = "/dev/ttyUSB0"):
#         log.info("Connecting to GRBL via serial")
#         self.s = serial.Serial(port, 115200) # WILL NEED TO CHANGE THIS PER DEVICE / OS
#         self.s.write(b"\r\n\r\n")
#         time.sleep(2)   # Wait for grbl to initialize 
#         # Wake up grbl
#         self.s.flushInput()  # Flush startup t
#         log.info("Input flushed")


#     def serial_disconnect(self):
#         self.s.close()

#     def send_line_serial(self):
#         line = self.g_code[self._n_line]
#         log.info("Sending {}".format(line))
#         self.s.write(str.encode("{}\n".format(line))) # Send g-code block to grbl
#         grbl_out = self.s.readline() # Wait for grbl response with carriage return
#         log.info(' : ' + str(grbl_out.strip()))
#         self._n_line += 1
    
if __name__ == "__main__":

    # for connection to 
    controller = MachineControl(100, 100, serial_port="COM4")

    controller.serial_connect_port()
    controller.jog_x(10)
    print(controller.is_connected())
    time.sleep(10)    
