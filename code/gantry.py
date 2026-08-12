import logging as log
import serial
import time
from threading import Thread, Lock
import re
import utils

log.basicConfig(format='%(process)d-%(levelname)s-%(message)s', level=log.INFO)

class Gantry:
    """Abstraction of most of the GRBL protocols.
    """
    def __init__(self, serial_port = "/dev/ttyUSB0", quiet=True):
        self.config = utils.load_config()

        self.quiet = quiet
        self._serial_port = serial_port # windows should be a "COM[X]" port which will vary per device

        # machine settings
        # fast z is 100, slow z is 15
        # fast xy is 500, slow xy is 200
        self.feed_rate_z = self.config["gantry"]["FEED_RATE_DEFAULT_Z"]
        self.feed_rate_xy = self.config["gantry"]["FEED_RATE_DEFAULT_XY"] 

        # Set gantry acceleration limits
        self.acceleration_slow_x = self.config["gantry"]["ACCELERATION_SLOW_X"]
        self.acceleration_slow_y = self.config["gantry"]["ACCELERATION_SLOW_Y"]
        self.acceleration_slow_z = self.config["gantry"]["ACCELERATION_SLOW_Z"]
        self.acceleration_fast_x = self.config["gantry"]["ACCELERATION_FAST_X"]
        self.acceleration_fast_y = self.config["gantry"]["ACCELERATION_FAST_Y"]
        self.acceleration_fast_z = self.config["gantry"]["ACCELERATION_FAST_Z"]

        
        self.s = None
        self.stop_threads = False

        self._x = None
        self._y = None
        self._z = None

        self.position_lock = Lock()
        self.send_command_lock = Lock() # adding lock for send command so that we can correctly associate GRBL responses to the corresponding command
        self.state_lock = Lock()
        self._state = None
        
        self.thread = Thread(target=self.position_monitor)

    def position_monitor(self):
        """Target function for thread to query GRBL state at approximately 5Hz.
        """
        cmd = "?"
        # Set WPos status reports
        self._send_command("$10=2")
        
        while not self.stop_threads:
            grbl_out_list = self._send_command(cmd)
        
            for grbl_out in grbl_out_list:
                ## print(f"{grbl_out} is state in position monitor")
                if "ok" in grbl_out:
                    continue
                elif "WPos" in grbl_out:
                    self.position_lock.acquire()
                    try:
                        _x, _y, _z = self.parse_coordinates(grbl_out)
                        self._x = _x
                        self._y = _y
                        self._z = _z
                    except:
                        log.error("Response with unparsable coordinates: {}".format(grbl_out))
                    
                    self.position_lock.release()

                    self.parse_state(grbl_out)

                    if not self.quiet:
                        log.info("X {} \nY {}\nZ{}\n".format(_x, _y, _z))
                else:
                    if not self.quiet:
                        log.error("No WPos found in status report return. \nGRBL Out: {}\n".format(grbl_out))
            time.sleep(0.2)

    def get_xyz(self)->tuple[float,float,float]:
        """Thread safe get function to retrieve the gantry position.

        Returns:
            tuple[float,float,float]: The X, Y, and Z position of the gantry from the most recent status report. 
        """
        self.position_lock.acquire()
        x, y, z = self._x, self._y, self._z
        self.position_lock.release()

        return x, y, z
    
    def parse_coordinates(self, grbl_status:str)->tuple[float,float,float]:
        """Extract the coordinates from the status report delivered by GRBL.

        Args:
            grbl_out (str): Response from GRBL after '?' command.

        Raises:
            ValueError: Raised when a coordinate cannot be parsed from the GRBL response.   

        Returns:
            tuple[float,float,float]: The X, Y, and Z position of the gantry from the most recent status report. 
        """
        # Use a regular expression to find the X, Y, and Z values
        match = re.search(r'WPos:([-+]?\d*\.?\d+),([-+]?\d*\.?\d+),([-+]?\d*\.?\d+)', grbl_status) # searches for integers and floats separated by commas after "WPos:"
        if match:
            x, y, z = map(float, match.groups())
            return x, y, z
        else:
            raise ValueError("The input string does not contain valid coordinates")

    def parse_state(self, grbl_status:str)->None:
        """Parse the state from the GRBL status report.

        Args:
            grbl_out (str): Response from GRBL after '?' command.

        Returns:
            str: The current GRBL machine state.
        """
        acquired = self.state_lock.acquire(timeout = 3)
        if acquired:
            if "ALARM" in grbl_status:
                log.info("GRBL ALARM SOUNDED: {}".format(grbl_status))
                self._state = "Alarm"
                self.state_lock.release()
            elif "Idle" in grbl_status:
                self._state = "Idle"
                self.state_lock.release()
            elif "Jog" in grbl_status:
                self._state = "Jog"
                self.state_lock.release()
            elif "Alarm" in grbl_status:
                self._state = "Alarm"
                self.state_lock.release()
            elif "Home" in grbl_status:
                self._state = "Home"
                self.state_lock.release()
            elif "Run" in grbl_status:
                self._state = "Run"
                self.state_lock.release()
            elif "Hold" in grbl_status:
                self._state = "Hold"
                self.state_lock.release()
            elif "Door" in grbl_status:
                self._state = "Door"
                self.state_lock.release()
            elif "Check" in grbl_status:
                self._state = "Check"
                self.state_lock.release()
            elif "Sleep" in grbl_status:
                self._state = "Sleep"
                self.state_lock.release()
            else:
                log.error("Parsed State Error: {}".format(grbl_status))
                self._state = "Temp"
        else:
            log.error("Could not acquire state lock before timeout (parse).")
            return "Temp"
        
    def block_for_jog(self):
        """Blocking function to help with tasks that need to be synchronized.
        """
        # Block while jog waits to complete. Make sure that the monitor can update its state before trying to test state
        time.sleep(0.5)
        while self.get_state() == "Jog":
            time.sleep(0.5)
    
    def get_state(self):
        """Get machine state with thread safety.
        """
        acquired = self.state_lock.acquire(timeout=3)
        if acquired:
            state = self._state
            self.state_lock.release()
        else:
            log.error("Could not acquire state lock before timeout.")
            state = "Jog"
        return state
    
    def _send_command(self, cmd:str) -> list:
        """Function to send a G-code command to GRBL via serial. Should be treated as a private function to prevent erroneous commands.

        Args:
            cmd (str): The G-Code command to send.

        Returns:
            str: All GRBL responses to command concatenated into one string and separated by \n.
        """
        if not self.quiet:
            log.info("Sending {}".format(cmd))

        # Using lock to verify that the GRBL response is the associated to the current command being sent. 
        # Don't send another command until you hear back. Also allows for safe alarm handling when that becomes a thing.
        grbl_out_list = []
        self.send_command_lock.acquire()
            # self.s.flush() # pretty sure this is not needed and may provide odd behaviour
        self.s.write(str.encode("{}\n".format(cmd.strip()))) # Send g-code block to grbl. Strip any accidental EOL

        while self.s.in_waiting > 0:
            grbl_out = self.s.readline().strip().decode("utf-8")
            self.grbl_handshake(grbl_out)
            grbl_out_list.append(grbl_out)

        self.send_command_lock.release()
        # log.info("Release send command lock. {}".format(time.time()))
        return grbl_out_list

    def grbl_handshake(self, grbl_out:str):
        """Interpreting GRBL responses to G-code commands in readable text. See https://github.com/gnea/grbl/wiki/Grbl-v1.1-Interface

        Args:
            grbl_out_list (str): The responses concatenated into one string from GRBL after it receives a command.
        """

        if "<" in grbl_out: # Contains push message with response from '?' command
            if not self.quiet:
                log.info("GRBL Status: {}".format(grbl_out)) # 
        elif "[" in grbl_out:
            log.info("GRBL Message: {}".format(grbl_out))
        elif "ok" in grbl_out:
            if not self.quiet:
                log.info("Command sent and OK")
        elif "error" in grbl_out:
            log.error("G-code error. See interface wiki for more details on the specific code. {} \n\n".format(grbl_out))
        elif "ALARM:10" in grbl_out:
            log.error("Homing fail. On dual axis machines, could not find the second limit switch for self-squaring. {} \n\n".format(grbl_out))
        elif "ALARM:1" in grbl_out: # TODO: add halting for the alarms 
            log.error("Hard limit triggered. Machine position is likely lost due to sudden and immediate halt. Re-homing is highly recommended. {} \n\n".format(grbl_out))
        elif "ALARM:2" in grbl_out:
            log.error("G-code motion target exceeds machine travel. Machine position safely retained. Alarm may be unlocked. {} \n\n".format(grbl_out))
        elif "ALARM:3" in grbl_out:
            log.error("Reset while in motion. Grbl cannot guarantee position. Lost steps are likely. Re-homing is highly recommended. {} \n\n".format(grbl_out))
        elif "ALARM:6" in grbl_out:
            log.error("Homing fail. Reset during active homing cycle. {} \n\n".format(grbl_out))
        elif "ALARM:8" in grbl_out:
            log.error("Homing fail. Cycle failed to clear limit switch when pulling off. Try increasing pull-off setting or check wiring. {} \n\n".format(grbl_out))
        elif "ALARM:9" in grbl_out:
            log.error("Homing fail. Could not find limit switch within search distance. Defined as 1.5 * max_travel on search and 5 * pulloff on locate phases. {} \n\n".format(grbl_out))
       
        else:
            log.error("GRBL Response : {}".format(grbl_out))

    def jog_absolute_xyz(self, x: float, y: float, z: float, feed: int = None) -> None:
        """Jog abstraction for jogging in the X, then Y, then Z axes.

        Args:
            x (float): X location to jog to in mm.
            y (float): Y location to jog to in mm.
            z (float): Z location to jog to in mm.    
            feed (int, optional): Feed rate to move at in mm/sec. Defaults to None.
        """
        if feed is not None:
            feed_rate = feed
        else:
            feed_rate = self.feed_rate_xy

        cmd = "$J=G90 G21 X{} F{}".format(x, feed_rate)
        self._send_command(cmd)
        cmd = "$J=G90 G21 Y{} F{}".format(y, feed_rate)
        self._send_command(cmd)
        cmd = "$J=G90 G21 Z{} F{}".format(z, feed_rate)
        self._send_command(cmd)
        
    def jog_absolute_xy(self, x:float, y:float, feed:int = None) -> None:
        """Jog abstraction for jogging in the X and Y axes simultaneously.

        Args:
            x (float): X location to jog to in mm.
            y (float): Y location to jog to in mm.
            feed (int, optional): Feed rate to move at in mm/sec. Defaults to None.
        """
        if feed is not None:
            feed_rate = feed
        else:
            feed_rate = self.feed_rate_xy
        cmd = "$J=G90 G21 X{} Y{} F{}".format(x, y, feed_rate)
        _ = self._send_command(cmd)

    def jog_absolute_x(self, pos, feed = None) -> None:
        if feed is not None:
            feed_rate = feed
        else:
            feed_rate = self.feed_rate_xy
        cmd = "$J=G90 G21 X{} F{}".format(pos, feed_rate)
        _ = self._send_command(cmd)

    def jog_absolute_y(self, pos, feed = None) -> None:
        if feed is not None:
            feed_rate = feed
        else:
            feed_rate = self.feed_rate_xy
        cmd = "$J=G90 G21 Y{} F{}".format(pos, feed_rate)
        _ = self._send_command(cmd)

    def jog_absolute_z(self, pos, feed = None) -> None:
        if feed is not None:
            feed_rate = feed
        else:
            feed_rate = self.feed_rate_z
        cmd = "$J=G90 G21 Z{} F{}".format(pos, feed_rate)
        _ = self._send_command(cmd)

    def jog_relative_x(self, dist, feed = None) -> None:
        '''
        Jog a distance (mm) from the current location in the x plane, NOT to an absolute position. 
        +dist moves to the +x
        -dist moves to the -x
        '''
        if feed is not None:
            feed_rate = feed
        else:
            feed_rate = self.feed_rate_xy
        cmd = "$J=G91 G21 X{} F{}".format(dist, feed_rate)
        _ = self._send_command(cmd)

    def jog_relative_y(self, dist, feed = None) -> None:
        '''
        Jog a distance (mm) from the current location in the y plane, NOT to an absolute position. 
        +dist moves to the +y
        -dist moves to the -y
        '''
        if feed is not None:
            feed_rate = feed
        else:
            feed_rate = self.feed_rate_xy
        cmd = "$J=G91 G21 Y{} F{}".format(dist, feed_rate)
        _ = self._send_command(cmd)

    def jog_relative_z(self, dist, feed = None) -> None:
        '''
        Jog a distance (mm) from the current location in the z plane, NOT to an absolute position. 
        +dist moves to the +z
        -dist moves to the -z
        '''
        if feed is not None:
            feed_rate = feed
        else:
            feed_rate = self.feed_rate_z
        cmd = "$J=G91 G21 Z{} F{}".format(dist, feed_rate)
        _ = self._send_command(cmd)

    def jog_cancel(self) -> None:
        """Immediately cancels the current jog state by a feed hold and
        automatically flushing any remaining jog commands in the buffer.
        Command is ignored, if not in a JOG state or if jog cancel is already
        invoked and in-process.
        """
        #  cmd = "\x85"
        #  _ = self._send_command(cmd)
        self.s.write(bytes([0x85]))

    def pause(self) -> None:
        cmd = "M0"
        _ = self._send_command(cmd)

    def resume(self) -> None:
        cmd = "~"
        _ = self._send_command(cmd)

    def homing_sequence(self) -> None:
        """Home the machine.
        """
        cmd = "$H"
        _ = self._send_command(cmd)

    def set_origin(self) -> None:
        cmd = "G10 P0 L20 X0 Y0 Z0"
        _ = self._send_command(cmd)

    def log_serial_out(self, s_out):
        if not self.quiet:
            log.info(' : ' + str(s_out.strip()))

    def set_acceleration(self, fast: bool = False) -> None:
        # mm / sec^2
        # set xyz feed acceleration
        if fast:
            _ = self._send_command("$120={}".format(self.acceleration_fast_x))
            _ = self._send_command("$121={}".format(self.acceleration_fast_y))
            _ = self._send_command("$122={}".format(self.acceleration_fast_z))
        else:
            _ = self._send_command("$120={}".format(self.acceleration_slow_x))
            _ = self._send_command("$121={}".format(self.acceleration_slow_y))
            _ = self._send_command("$122={}".format(self.acceleration_slow_z))

    def set_soft_limits(self) -> None:
        x_soft_limit_mm = 900 # mm
        y_soft_limit_mm = 900
        z_soft_limit_mm = 300
        _ = self._send_command("$131={}".format(x_soft_limit_mm))
        _ = self._send_command("$132={}".format(y_soft_limit_mm))
        _ =self._send_command("$133={}".format(z_soft_limit_mm))


        
        

    def serial_connect_port(self) -> None:
        """Connect via serial to GRBL as done in the given example. https://github.com/gnea/grbl/blob/master/doc/script/simple_stream.py 
        """
        log.info("Connecting to GRBL via serial")
        if self.s is None:
            self.s = serial.Serial(self._serial_port, 115200) # WILL NEED TO CHANGE THIS PER DEVICE / OS
            time.sleep(2)# Wait for grbl to initialize 

            # Wake up grbl
            log.info("Writing to wake grbl")
            self.s.write(b"\r\n\r\n")
            log.info("Flush input")
            self.s.flushInput()  # Flush startup t
            grbl_out = self.s.readline() # Wait for grbl response with carriage return
            grbl_out_str = grbl_out.decode("utf-8")

            log.info(grbl_out_str)

            self.log_serial_out(grbl_out)
            log.info("Input flushed")
            log.info("Starting Position Monitor")
            log.info("Connected to GRBL via serial. Ready to control.")
       
            self.thread.start() 
            self.set_acceleration(fast=True)        
            # self .set_soft_limits() # causing errors i think
            

    def serial_disconnect_port(self):
    	#TODO: somehow make it so we dont have to reset blackbox?
        self.s.close()

    def quit(self):
        if self.s is not None:
            if self.s.is_open:
                self.s.close()
            self.stop_threads = True
    
if __name__ == "__main__":
    s = serial.Serial('/dev/ttyUSB0',115200)
    f = ["?", "?", "?", "?", "?", "?", "?", "?", "?", "?", "?", "?", "?", "?", "G91 Xk F200", "G91 Y-10 F50", "G91 Y-0.00000001 F50"]

    g = Gantry()
    # Wake up grbl
    g.serial_connect_port()

    # Stream g-code to grbl
    for line in f:
        g._send_command(line)
            
        time.sleep(0.2)

    # Wait here until grbl is finished to close serial port and file.
    input("  Press <Enter> to exit and disable grbl.") 

    # Close file and serial port

    s.close()    
