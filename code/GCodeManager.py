import logging as log
import math
import serial
import time

log.basicConfig(format='%(process)d-%(levelname)s-%(message)s', level=log.INFO)

class GCodeManager:
    def __init__(self, cookie_width_mm: int, cookie_height_mm: int, image_width_mm: int, image_height_mm: int, feed_rate: int, overlap_percentage: int, start_point: tuple[int, int]=(0, 0)) -> None:
        self.cookie_width_mm = cookie_width_mm
        self.cookie_height_mm = cookie_height_mm
        self.image_width_mm = image_width_mm
        self.image_height_mm = image_height_mm
        self.feed_rate = feed_rate # mm/min
        self.overlap_percentage = overlap_percentage
        self.start_point = start_point
        self.max_z = 100 # mm
        self.g_code = self.generate_serpentine()
        self._n_line = 0 # current line of g_code 
        # self.serial_connect()


    def generate_serpentine(self) -> list[str]:
        # See TreeRings/docs/diagrams/G_code_serpentine_logic.png for graphical representation of code
        g_code = []

        start_x = self.start_point[0]
        start_y = self.start_point[1]

        # move the center of the frame to align the window with the edge of the cookie
        x = start_x + self.image_width_mm / 2
        y = start_y + self.image_height_mm / 2

        # Move to the specified starting point, raise z to max value to avoid lens collision

        #TODO: verify that this is updates position when endstops are hit
        g_code.append(f"$H") # home first to get reference system, 
        # g_code.append(f"G0 X{start_x} Y{start_y} Z{self.max_z}") 
        # g_code.append(f"G0 X{start_x} Y{start_y}") 
        g_code.append("G21") # Units are in mm

        # More than 0.00 precision is unrealistic with the machinery
        overlap_x = round(self.image_width_mm * self.overlap_percentage / 100, 2)
        overlap_y = round(self.image_height_mm * self.overlap_percentage / 100, 2)
        log.info(overlap_x)
        log.info(overlap_y)

        # TODO: add logic / user input / something to move z to be in focus
        x_step_size = self.image_width_mm - overlap_x
        y_step_size = self.image_height_mm - overlap_y 

        x_steps = math.ceil(self.cookie_width_mm / x_step_size)
        y_steps = math.ceil(self.cookie_height_mm / y_step_size)
        total_images = x_steps * y_steps
        
        log.info(x_steps)
        log.info(y_steps)
        log.info("Creating G-Code for {} serpentine images".format(total_images))
        
        # begin serpentine logic
        g_code.append(f"G1 X{x} Y{y} F{self.feed_rate}") # set and forget feed

        for y_step in range(0, y_steps):

            # Move in X-direction with overlap
            for _ in range(0, x_steps - 1): # -1 because the y movement counts as the first image in the new row
                x = round(x + x_step_size, 2)
                g_code.append(f"G1 X{x} Y{y}")

            # Move down one step in the +Y-direction with overlap
            y = round(y + y_step_size, 2)

            # Don't go further down after the final row is finished
            if y_step != y_steps - 1:
                g_code.append(f"G1 X{x} Y{y}")

            x_step_size *= -1 # switch X directions

        # End program
        g_code.append("M2")

        return g_code
    
    def serial_connect(self):
        log.info("Connecting to GRBL via serial")
        self.s = serial.Serial('COM4',115200) # WILL NEED TO CHANGE THIS PER DEVICE / OS
        self.s.write(b"\r\n\r\n")
        time.sleep(2)   # Wait for grbl to initialize 
        # Wake up grbl
        self.s.flushInput()  # Flush startup text in serial input

    def serial_connect_port(self, port = "ttyS0"):
        log.info("Connecting to GRBL via serial")
        self.s = serial.Serial(port, 115200) # WILL NEED TO CHANGE THIS PER DEVICE / OS
        self.s.write(b"\r\n\r\n")
        time.sleep(2)   # Wait for grbl to initialize 
        # Wake up grbl
        self.s.flushInput()  # Flush startup t

    def serial_disconnect(self):
        self.s.close()

    def send_line_serial(self):
        line = self.g_code[self._n_line]
        log.info("Sending {}".format(line))
        self.s.write(str.encode("{}\n".format(line))) # Send g-code block to grbl
        grbl_out = self.s.readline() # Wait for grbl response with carriage return
        log.info(' : ' + str(grbl_out.strip()))
        self._n_line += 1
    
if __name__ == "__main__":

    COOKIE_WIDTH_MM = 200
    COOKIE_HEIGHT_MM = 200
    IMAGE_WIDTH_MM = 4
    IMAGE_HEIGHT_MM = 5
    FEED_RATE = 500 # mm / min
    PERCENT_OVERLAP = 20
    START_POINT = (20, 20)

    GCM = GCodeManager(COOKIE_WIDTH_MM, COOKIE_HEIGHT_MM, IMAGE_WIDTH_MM, IMAGE_HEIGHT_MM, FEED_RATE, PERCENT_OVERLAP, START_POINT)
    GCM.serial_connect()

    for line in GCM.g_code:
        # log.info("Waiting for user input")
        # input()
        GCM.send_line_serial()

    log.info(len(GCM.g_code))