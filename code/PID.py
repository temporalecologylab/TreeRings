import time
import numpy as np

class AsynchronousPID:
    def __init__(self, Kp, Ki, Kd, setpoint = 0):
        self.Kp = Kp
        self.Ki = Ki
        self.Kd = Kd
        self.setpoint = setpoint
        self._previous_error = 0.0
        self._integral = 0.0
        self._previous_time = time.time()
    
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
        
        # PID output
        output = P + I + D
        
        # Update previous values
        self._previous_error = error
        self._previous_time = current_time
        
        return output

def adjust_focus(control_signal, scale_factor):
    # Convert the control signal to millimeters of movement using the scale factor
    movement_mm = control_signal * scale_factor
    return movement_mm  

def move_focus_motor(movement_mm):
    # Placeholder function to move the focus motor by the specified distance in millimeters
    # This would interact with the actual motor control hardware
    print(f"Moving focus motor by {movement_mm:.2f} millimeters")

def get_current_focus_score():
    # Placeholder function to get the current focus score
    # This would involve image processing to evaluate the focus quality
    return 80  # Example focus score

if __name__ == "__main__":
    import matplotlib.pyplot as plt
    
    # Example usage
    def get_index(n_images, prev_value):
        change = np.random.normal(0, 1)

        val = prev_value + change

        if val > n_images:
            val = n_images
        elif val < 0:
            val = 0

        return val 
    
    n_images_per_set = 9
    setpoint = 5  # desired index of image with highest normalized variance score
    pid = AsynchronousPID(Kp=1.0, Ki=0.1, Kd=0.05, setpoint=setpoint)
    scale_factor = 0.1  # Example scale factor: 1 unit of control signal = 0.1 mm of movement
    i = 0
    prev_image_index = 5

    # Plot data
    x = [i]
    measured = [0]
    control = [0]
    
    plt.ion()

    plt.plot(x, measured, label = "Measured", c = "green")
    graph = plt.plot(x,control, label = "Control", c = "red")[0]
    plt.ylim(-n_images_per_set,n_images_per_set)
    plt.pause(1)


    while True:
        i+=1
        measured_value = get_index(n_images_per_set, prev_image_index)
        prev_image_index = measured_value
        control_variable = pid.update(measured_value)
        x.append(i)
        measured.append(measured_value)
        control.append(adjust_focus(control_variable, scale_factor)) # Convert and apply the control signal

        graph.remove()

        plt.plot(x, measured, label = "Measured", c = "green")
        graph = plt.plot(x,control, label = "Control", c = "red")[0]
        plt.xlim(x[0], x[-1])
        plt.pause(0.25)
        time.sleep(2)  # Wait for the next sample (2 seconds in this example)
