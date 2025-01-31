import cv2
import time
import numpy as np
import math
from pathlib import Path
from datetime import datetime

class Sample:
    def __init__(self, sample_width_mm: int, sample_height_mm: int, species:str, id1:str, id2:str, notes:str, image_width_mm:float, image_height_mm:float, is_core:bool,  percent_overlap:int = 50, is_vertical:bool = True, x:float = None, y:float = None, z:float = None):
        """Class which contains the necessary information for each sample that needs to be digitized. Data comes from user inputs from GUI. Data is saved in metadata.json files alongside stitched images

        Args:
            sample_width_mm (int): Width of minimum bounding rectangle around edges of the sample
            sample_height_mm (int): Height of minimum bounding rectangle around the edges of the sample
            species (str): Species descriptor
            id1 (str): Additional species ID1
            id2 (str): Additional specied ID 2
            notes (str): Additional notes for ambiguity in sample
            image_width_mm (float): Width in mm of the field of view of a single image. Helpful to print a 1mm x 1mm grid to measure
            image_height_mm (float): Height in mm of the field of view of a single image. Helpful to print a 1mm x 1mm grid to measure
            is_core (bool): Is the sample a core? 
            percent_overlap (int, optional): Desired overlap between two images. Defaults to 50.
            is_vertical (bool, optional): If is_core, is the length of the core aligned vertically? Defaults to True.
            x (float, optional): X position of the center of the sample in the gantry coordinate system. Defaults to None.
            y (float, optional): Y position of the center of the sample in the gantry coordinate system. Defaults to None.
            z (float, optional): Z position of the center of the sample in the gantry coordinate system. Defaults to None.
        """
        self.width = sample_width_mm
        self.height = sample_height_mm
        self.percent_overlap = percent_overlap
        self._center = (round(x, 4),round(y, 4),round(z, 4))
        tl_x = x - (self.width/2)
        tl_y = y + (self.height/2)
        tl_z = z
        self._top_left = (tl_x, tl_y, tl_z)
        self.species = species
        self.id1 = id1
        self.id2 = id2
        self.notes = notes

        dirtime = datetime.now().strftime("%H_%M_%S")
        directory = "./{}_{}_{}_{}".format(species, id1, id2, dirtime)
        Path(directory).mkdir()
        self.directory = directory

        self.image_width_mm = image_width_mm
        self.image_height_mm = image_height_mm
        self.rows, self.cols, self.x_step_size, self.y_step_size = self.calculate_grid_params()
        self.targets_top, self.targets_bot = self.calculate_image_locations(self.rows, self.cols, self.x_step_size, self.y_step_size) # Each index of the (-1, 5) shape array is (X, Y, Z, row, col)
        self.background = []
        self.background_std = []
        self.coordinates = []
        self.focus_index = []
        self.nvar = []
        self.is_core = is_core
        self.is_vertical = is_vertical

    def calculate_grid_params(self):
        """Calculates the amount of rows and columns necessary to traverse the sample.

        Returns:
            int: Count of rows, always odd
            int: Count of cols, always odd
            float: step size for translation in x direction 
            float: step size for translation in y direction 
        """
        overlap_x = round(self.image_width_mm * self.percent_overlap / 100, 3)
        overlap_y = round(self.image_height_mm * self.percent_overlap / 100, 3)

        x_step_size = self.image_width_mm - overlap_x
        y_step_size = self.image_height_mm - overlap_y 

        if x_step_size == 0:
            cols = 1
        else:
            cols = math.ceil(self.width / x_step_size)

        if y_step_size == 0:
            rows = 1
        else:
            rows = math.ceil(self.height / y_step_size)

        # Verify that there are an odd number of rows and columns to make grid calculation easier
        if cols % 2 != 1:
            cols += 1
        
        if rows % 2 != 1:
            rows += 1

        return rows, cols, x_step_size, y_step_size

    def calculate_image_locations(self, rows, cols, x_step_size, y_step_size):
        """Generate the coordinates for the centerpoint of each image.

        """
        # Depth of 5 for X, Y, Z, row, col
        grid = np.zeros(shape = (rows, cols, 5))
        
        middle_row = rows // 2
        middle_col = cols // 2

        # XYZ calculations
        x_offsets = np.cumsum(np.repeat(x_step_size, cols // 2))
        x_offsets_reverse = x_offsets[::-1] * -1
        
        x_array_1d = np.concatenate((x_offsets_reverse, np.array([0]), x_offsets))
        x_offsets_2d = np.tile(x_array_1d, (rows, 1))

        y_offsets = np.cumsum(np.repeat(y_step_size, rows // 2))
        y_offsets_reverse = y_offsets[::-1] * -1

        y_array_1d = np.concatenate((y_offsets_reverse, np.array([0]), y_offsets))
        y_offsets_2d = np.tile(y_array_1d[np.newaxis].transpose(), (1, cols))

        # Add center to grid of zeros 
        grid[:, :, 0:3] += np.array(self._center)

        # Add X and Y offsets to grid
        grid[:, :, 0] += x_offsets_2d
        grid[:, :, 1] += y_offsets_2d

        # Row and Column definitions
        rows_array = np.arange(rows)
        cols_array = np.arange(cols)

        rows_2d = np.tile(rows_array[np.newaxis].transpose(), (1, cols))
        cols_2d = np.tile(cols_array, (rows, 1))

        # Assign row and cols to points
        grid[:, :, 3] = rows_2d
        grid[:, :, 4] = cols_2d

        # Assign initial X,Y,Z,ROW,COL to center of grid
        grid_long = grid.reshape((-1,5))
        center_index = math.ceil(len(grid_long) / 2)

        # Separate top half of points and bottom half of points
        top_half_targets = grid_long[0:center_index][::-1]
        bot_half_targets = grid_long[center_index:]

        # Now we need different sorting if the row is even or odd to make sure serpentine occurs
        # Center row is guaranteed to be on an even row

        if middle_row % 2 == 1:
            # For top half, we need ascending col order on even rows and descending col order on odd rows, and overall descending on rows
            top_half_even = top_half_targets[top_half_targets[:, 3] % 2 == 0]
            idx = np.lexsort((top_half_even[:,4], top_half_even[:,3] * -1))
            top_half_targets[top_half_targets[:, 3] % 2 == 0] = top_half_even[idx]


            # For bot half, we need descending col order on even rows and ascending col order on odd rows, and overall ascending on rows 
            bot_half_odd = bot_half_targets[bot_half_targets[:, 3] % 2 == 1]
            idx = np.lexsort((bot_half_odd[:,4], bot_half_odd[:, 3])) 
            bot_half_targets[bot_half_targets[:,3] % 2 == 1] = bot_half_odd[idx]

            bot_half_even = bot_half_targets[bot_half_targets[:, 3] % 2 == 0]
            idx = np.lexsort((bot_half_even[:,4] * -1, bot_half_even[:,3]))
            bot_half_targets[bot_half_targets[:, 3] % 2 == 0] = bot_half_even[idx]
        else:
             # For top half, we need descending col order on even rows and ascending col order on odd rows, and overall descending on rows
            top_half_odd = top_half_targets[top_half_targets[:, 3] % 2 == 1]
            idx = np.lexsort((top_half_odd[:,4], top_half_odd[:,3] * -1))
            top_half_targets[top_half_targets[:, 3] % 2 == 1] = top_half_odd[idx]

            # For bot half, we need ascending col order on even rows and descending col order on odd rows, and overall ascending on rows 
            bot_half_odd = bot_half_targets[bot_half_targets[:, 3] % 2 == 1]
            idx = np.lexsort((bot_half_odd[:,4] * -1, bot_half_odd[:, 3])) 
            bot_half_targets[bot_half_targets[:,3] % 2 == 1] = bot_half_odd[idx]


        return top_half_targets, bot_half_targets

    def get_center_location(self):
        """Retrieve the center location of the sample

        Returns:
            tuple[float]: X, Y, Z coordinates of the center 
        """
        return self._center
    
    def get_top_left_location(self):
        """Retrieve the top left location of the sample

        Returns:
            tuple[float]: X, Y, Z coordintes of top left corner of sample
        """
        return self._top_left
    

def main():
    sample = Sample(150, 0, "test", "test", "test", "test", 5, 3, 30, 0, 0, 0)
    print(sample.targets_top)
    print(sample.targets_bot)

if __name__ == "__main__":
    main()