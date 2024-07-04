import logging as log
import serial
import time

log.basicConfig(format='%(process)d-%(levelname)s-%(message)s', level=log.INFO)

class Gantry:
    def __init__(self, serial_port = "/dev/ttyUSB0"):
        pass

        self._serial_port = serial_port # windows should be a "COM[X]" port which will vary per device

        # machine settings
        self.feed_rate_z = 15
        self.feed_rate_xy = 200 

        self.feed_rate_fast_z = 100
        self.feed_rate_fast_xy = 500

        # sample information
        self.cookie_samples = []
        self.core_samples = []

        self.s = None

    def _send_command(self, cmd) -> str:
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
        self._send_command(cmd)

    def jog_y(self, dist) -> None:
        '''
        Jog a distance (mm) from the current location in the y plane, NOT to an absolute position. 
        +dist moves to the +y
        -dist moves to the -y
        '''
        cmd = "$J=G91 G21 Y{} F{}".format(dist, self.feed_rate_xy)
        self._send_command(cmd)

    def jog_z(self, dist) -> None:
        '''
        Jog a distance (mm) from the current location in the z plane, NOT to an absolute position. 
        +dist moves to the +z
        -dist moves to the -z
        '''
        cmd = "$J=G91 G21 Z{} F{}".format(dist, self.feed_rate_z)
        self._send_command(cmd)
        
    def jog_fast_x(self, dist) -> None:
        '''
        Jog a distance (mm) from the current location in the x plane, NOT to an absolute position. 
        +dist moves to the +x
        -dist moves to the -x

        '''
        cmd = "$J=G91 G21 X{} F{}".format(dist, self.feed_rate_fast_xy)
        self._send_command(cmd)

    def jog_fast_y(self, dist) -> None:
        '''
        Jog a distance (mm) from the current location in the y plane, NOT to an absolute position. 

        +dist moves to the +y
        -dist moves to the -y
        '''
        cmd = "$J=G91 G21 Y{} F{}".format(dist, self.feed_rate_fast_xy)
        self._send_command(cmd)

    def jog_fast_z(self, dist) -> None:

        '''
        Jog a distance (mm) from the current location in the z plane, NOT to an absolute position. 
        +dist moves to the +z
        -dist moves to the -z
        '''
        cmd = "$J=G91 G21 Z{} F{}".format(dist, self.feed_rate_fast_z)
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

    def query_state(self) -> None:
        """Query the state of the machine. Updates the attribute if the machine is connected
        """
        cmd = "?"
        res = self._send_command(cmd)
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

    
