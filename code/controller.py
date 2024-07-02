import gantry
import focus
import cookie
import camera
import logging as log


class Controller:

    def __init__(self):
        self.cookies = []
        self.gantry = gantry.Gantry()
        self.camera = camera.Camera()


    def quit(self):
        log.info("Ending Camera Stream")
        self.camera.end_camera_filesave()
        log.info("Disconnecting serial port")
        self.gantry.serial_disconnect_port()

    def serial_connect(self):
        self.gantry.serial_connect_port()

    def jog_y_plus(self):
        log.info("jog +{} mm y".format(self.jog_distance))
        self.gantry.jog_fast_y(self.jog_distance)

    def jog_y_minus(self):
        log.info("jog -{} mm y".format(self.jog_distance))
        self.gantry.jog_fast_y(self.jog_distance * -1)
    
    def jog_x_plus(self):
        log.info("jog +{} mm x".format(self.jog_distance))
        self.gantry.jog_fast_x(self.jog_distance)

    def jog_x_minus(self):
        log.info("jog -{} mm x".format(self.jog_distance))
        self.gantry.jog_fast_x(self.jog_distance * -1)
    
    def jog_z_plus(self):
        log.info("jog +{} mm z".format(self.jog_distance))
        self.gantry.jog_fast_z(self.jog_distance)

    def jog_z_minus(self):
        log.info("jog -{} mm z".format(self.jog_distance))
        self.gantry.jog_fast_z(self.jog_distance * -1)
    
        