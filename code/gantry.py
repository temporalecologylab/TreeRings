import logging as log
import serial
import time
from threading import Thread, Lock
import re
import utils

log.basicConfig(format='%(process)d-%(levelname)s-%(message)s', level=log.INFO)

class Gantry:
    def __init__(self, serial_port = "/dev/ttyUSB0", quiet=True):
        self.config = utils.load_config()


        self.quiet = quiet
        self._serial_port = serial_port # windows should be a "COM[X]" port which will vary per device

        # machine settings
        # fast z is 100, slow z is 15
        # fast xy is 500, slow xy is 200
        self.feed_rate_z = self.config["gantry"]["FEED_RATE_DEFAULT_Z"]
        self.feed_rate_xy = self.config["gantry"]["FEED_RATE_DEFAULT_XY"] 

        # sample information
        self.cookie_samples = []
        self.core_samples = []

        self.s = None
        self.stop_threads = False

        self._x = None
        self._y = None
        self._z = None

        self.position_lock = Lock()
        self.state = None
        
        self.thread = Thread(target=self.position_monitor)

    def position_monitor(self):
        cmd = "?"
        # Set WPos status reports
        self._send_command("$10=2")
        while not self.stop_threads:
            res_str = self._send_command(cmd)

            if res_str is None:
                continue
            elif res_str[-2:] == "ok":
                continue
            elif "WPos" in res_str:
                self.position_lock.acquire()
                try:
                    _x, _y, _z = self.parse_coordinates(res_str)
                except:
                    log.info("Error reading parsing coordinates")
                    continue
                self._x = _x
                self._y = _y
                self._z = _z
                self.position_lock.release()
                self.state = self.parse_state(res_str)
                if not self.quiet:
                    log.info("X {} \nY {}\nZ{}\n".format(_x, _y, _z))

            time.sleep(0.2)

    def get_xyz(self):
        self.position_lock.acquire()
        x, y, z = self._x, self._y, self._z
        self.position_lock.release()

        return x, y, z
    
    def parse_coordinates(self, input_string):
        # Use a regular expression to find the X, Y, and Z values
        match = re.search(r'WPos:(-?\d+\.\d+),(-?\d+\.\d+),(-?\d+\.\d+)', input_string)
        if match:
            x, y, z = map(float, match.groups())
            return x, y, z
        else:
            raise ValueError("The input string does not contain valid coordinates")

    def parse_state(self, input_string):
        # Use a regular expression to find the X, Y, and Z values
        #print("STATE {}".format(self.state))
        if "Idle" in input_string:
            return "Idle"
        
        elif "Jog" in input_string:
            return "Jog"
    
    def block_for_jog(self):
        # Block while jog waits to complete. Make sure that the monitor can update its state before trying to test state
        time.sleep(0.5)
        while self.state == "Jog":
            time.sleep(0.5)
        return None
    
    def _send_command(self, cmd) -> str:
        def read_response(ser):
            response = ""

            try: 
                while ser.in_waiting > 0:
                    response += ser.readline().decode().strip() + "\n"
                return response
            except:
                log.info("Error reading serial")
                return None
        
        if not self.quiet:
            log.info("Sending {}".format(cmd))

        self.s.flush()
        self.s.write(str.encode("{}\n".format(cmd))) # Send g-code block to grbl
        return read_response(self.s)

    def jog_absolute_xyz(self, x, y, z) -> None:
        cmd = "$J=G90 G21 X{} Y{} Z{} F{}".format(x, y, z, self.feed_rate_xy)
        self._send_command(cmd)
        
    def jog_absolute_xy(self, x, y) -> None:
        cmd = "$J=G90 G21 X{} Y{} F{}".format(x, y, self.feed_rate_xy)
        self._send_command(cmd)

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
        if not self.quiet:
            log.info(' : ' + str(s_out.strip()))

    def set_acceleration(self, acc=50):
        # mm / sec^2
        # set xyz feed acceleration
        self._send_command("$120={}".format(acc))
        self._send_command("$121={}".format(acc))
        self._send_command("$122={}".format(acc))

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
        self.set_acceleration(50)        


    def serial_disconnect_port(self):
    	#TODO: somehow make it so we dont have to reset blackbox?
        self.s.close()

    def quit(self):
        if self.s is not None:
            if self.s.is_open:
                self.s.close()
            self.stop_threads = True
    
