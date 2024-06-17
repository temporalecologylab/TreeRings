import logging as log
import math
import serial
import time
from threading import Lock
from picamera2 import Picamera2
import cv2


log.basicConfig(format='%(process)d-%(levelname)s-%(message)s', level=log.INFO)

class CoreSample:
    pass

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
        self.feed_rate_z = 100
        self.feed_rate_xy = 500 

        # sample information
        self.cookie_samples = []
        self.core_samples = []

        # mutex for taking images
        self.mutex_camera = Lock()

        self.launch_rpi_cam()

    def add_cookie_sample(self, cookie_width_mm: int, cookie_height_mm: int, percent_overlap: int = 20) -> None:
        cookie = CookieSample(cookie_width_mm, cookie_height_mm, percent_overlap = percent_overlap)
        self.cookie_samples.append(cookie)

    def add_core_sample(self, core: CoreSample) -> None:
        self.core_samples.append(core) 

    def launch_rpi_cam(self):
        self.picam2 = Picamera2()
        self.picam2.configure(self.picam2.create_preview_configuration(main={"format": "XRGB8888", "size": (4056,3040)}))
        self.picam2.start()

    def capture_image(self):
        self.mutex_camera.acquire()
        img = self.picam2.capture_array()
        self.mutex_camera.release()
        return img

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
        time.sleep(2)   # Wait for grbl to initialize 
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

    def enable_soft_limits(self):
        cmd = "$20 1"
        self.send_command(cmd)
    
    def disable_soft_limits(self):
        cmd = "$20 0"
        self.send_command(cmd)

    def generate_serpentine(self, cookie: CookieSample) -> list[str]:
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
        g_code.append("$J=G91 G21 X{} F{}".format(x_step_size, self.feed_rate_xy)) # set and forget feed

        for y_step in range(0, y_steps):

            # Move in X-direction with overlap
            for _ in range(0, x_steps - 1): # -1 because the y movement counts as the first image in the new row
                x = round(x_step_size, 2)
                g_code.append(f"$J=G91 G21 X{x} F{self.feed_rate_xy}")

            # Move down one step in the +Y-direction with overlap
            y = round(y_step_size, 2)

            # Don't go further down after the final row is finished
            if y_step != y_steps - 1:
                g_code.append(f"$J=G91 G21 Y-{y} F{self.feed_rate_xy}")

            x_step_size *= -1 # switch X directions

        # End program
        # g_code.append("M2")
    
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