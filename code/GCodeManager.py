import logging as log
import math

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

    def generate_serpentine(self) -> list[str]:
        g_code = []

        start_x = self.start_point[0]
        start_y = self.start_point[1]

        # move the center of the frame to align the window with the edge of the cookie
        x = start_x + self.image_width_mm / 2
        y = start_y + self.image_height_mm / 2

        # Move to the specified starting point, raise z to max value to avoid lens collision

        #TODO: verify that this is updates position when endstops are hit
        g_code.append(f"G28 X Y") # home first to get reference system, 
        g_code.append(f"G0 X{start_x} Y{start_y} Z{self.max_z}") 

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
    
if __name__ == "__main__":
    GCG = GCodeManager(50, 40, 5, 4, 500, 20, (0, 0))
    g_code = GCG.generate_serpentine()
    
    print(len(g_code))