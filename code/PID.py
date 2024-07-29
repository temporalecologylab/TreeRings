import time
import numpy as np
import logging as log

log.basicConfig(format='%(process)d-%(levelname)s-%(message)s', level=log.INFO)

class AsynchronousPID:
    def __init__(self, Kp, Ki, Kd, setpoint):
        self.Kp = Kp
        self.Ki = Ki
        self.Kd = Kd
        self.setpoint = setpoint
        self._previous_error = 0.0
        self._integral = 0.0
        self._previous_time = time.time()
    
    def set_setpoint(self, setpoint):
        self.setpoint = setpoint

    def update(self, measured_value):
        current_time = time.time()
        dt = current_time - self._previous_time
        error = self.setpoint - measured_value
        
        # Proportional term
        P = self.Kp * error
        
        # Integral term
        self._integral += error * dt
        I = self.Ki * self._integral
        
        # Derivative term
        derivative = (error - self._previous_error) / dt if dt > 0 else 0.0
        D = self.Kd * derivative
        
        log.info(f"error: {error} P: {P} I: {I} D: {D}")
        
        # PID output
        output = P + I + D
        
        # Update previous values
        self._previous_error = error
        self._previous_time = current_time
        
        return output
