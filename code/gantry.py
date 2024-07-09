import logging as log
import serial
import time
from threading import Thread 
import re

log.basicConfig(format='%(process)d-%(levelname)s-%(message)s', level=log.INFO)

class Gantry:
    def __init__(self, serial_port = "/dev/ttyUSB0"):
        pass

        self._serial_port = serial_port # windows should be a "COM[X]" port which will vary per device

        # machine settings
        # fast z is 100, slow z is 15
        # fast xy is 500, slow xy is 200
        self.feed_rate_z = 15
        self.feed_rate_xy = 200 

        # sample information
        self.cookie_samples = []
        self.core_samples = []

        self.s = None
        self.stop_threads = False

        self.x = None
        self.y = None
        self.z = None
        
        self.thread = Thread(target=self.position_monitor)

    def position_monitor(self):
        cmd = "?"
        while not self.stop_threads:
            res_str = self._send_command(cmd)
            if res_str[-2:] == "ok":
                continue
            elif "WPos" in res_str:
                self.x, self.y, self.z = self.parse_coordinates(res_str)
                log.info("X {} \nY {}\nZ{}\n".format(self.x, self.y, self.z))
            time.sleep(1)

    def parse_coordinates(self, input_string):
        # Use a regular expression to find the X, Y, and Z values
        match = re.search(r'WPos:(-?\d+\.\d+),(-?\d+\.\d+),(-?\d+\.\d+)', input_string)
        if match:
            x, y, z = map(float, match.groups())
            return x, y, z
        else:
            raise ValueError("The input string does not contain valid coordinates")

    def _send_command(self, cmd) -> str:
        def read_response(ser):
            response = ""
            while ser.in_waiting > 0:
                response += ser.readline().decode().strip() + "\n"
            return response
        
        log.info("Sending {}".format(cmd))
        self.s.flush()
        self.s.write(str.encode("{}\n".format(cmd))) # Send g-code block to grbl
        return read_response(self.s)

    def jog_absolute_x(self, pos) -> None:
        cmd = "$J=G90 G21 X{} F{}".format(pos, self.feed_rate_xy)
        self._send_command(cmd)

    def jog_absolute_y(self, pos) -> None:
        cmd = "$J=G90 G21 Y{} F{}".format(pos, self.feed_rate_xy)
        self._send_command(cmd)

    def jog_absolute_z(self, pos) -> None:
        cmd = "$J=G90 G21 Z{} F{}".format(pos, self.feed_rate_z)
        self._send_command(cmd)

    def jog_relative_x(self, dist) -> None:
        '''
        Jog a distance (mm) from the current location in the x plane, NOT to an absolute position. 
        +dist moves to the +x
        -dist moves to the -x
        '''
        cmd = "$J=G91 G21 X{} F{}".format(dist, self.feed_rate_xy)
        self._send_command(cmd)

    def jog_relative_y(self, dist) -> None:
        '''
        Jog a distance (mm) from the current location in the y plane, NOT to an absolute position. 
        +dist moves to the +y
        -dist moves to the -y
        '''
        cmd = "$J=G91 G21 Y{} F{}".format(dist, self.feed_rate_xy)
        self._send_command(cmd)

    def jog_relative_z(self, dist) -> None:
        '''
        Jog a distance (mm) from the current location in the z plane, NOT to an absolute position. 
        +dist moves to the +z
        -dist moves to the -z
        '''
        cmd = "$J=G91 G21 Z{} F{}".format(dist, self.feed_rate_z)
        self._send_command(cmd)

    def jog_cancel(self) -> None:
        """Immediately cancels the current jog state by a feed hold and
        automatically flushing any remaining jog commands in the buffer.
        Command is ignored, if not in a JOG state or if jog cancel is already
        invoked and in-process.
        """
        cmd = "\x85"
        self._send_command(cmd)
    
    def pause(self) -> None:
        cmd = "M0"
        self._send_command(cmd)

    def resume(self) -> None:
        cmd = "~"
        self._send_command(cmd)

    def homing_sequence(self) -> None:
        cmd = "$H"
        self._send_command(cmd)
        self.query_state()

    def set_origin(self) -> None:
        cmd = "G10 P0 L20 X0 Y0 Z0"
        self._send_command(cmd)

    def query_state(self) -> None:
        """Query the state of the machine. Updates the attribute if the machine is connected
        """
        cmd = "?"
        res_str = self._send_command(cmd)
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
        log.info("Starting Position Monitor")
        self.thread.start() 


    def serial_disconnect_port(self):
    	#TODO: somehow make it so we dont have to reset blackbox?
        self.s.close()

    def quit(self):
        if self.s is not None:
            if self.s.is_open:
                self.s.close()
            self.stop_threads = True
    
