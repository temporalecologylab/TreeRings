import cv2
import time
import numpy as np
import math
from pathlib import Path
from datetime import datetime

class Cookie:
    def __init__(self, cookie_width_mm: int, cookie_height_mm: int, species:str, id1:str, id2:str, notes:str, image_width_mm:float, image_height_mm:float, percent_overlap:int = 50, x:float = None, y:float = None, z:float = None):
        """Class which contains the necessary information for each sample that needs to be digitized. Data comes from user inputs from GUI. Data is saved in metadata.json files alongside stitched images

        Args:
            cookie_width_mm (int): Width of minimum bounding rectangle around edges of the sample
            cookie_height_mm (int): Height of minimum bounding rectangle around the edges of the sample
            species (str): Species descriptor
            id1 (str): Additional species ID1
            id2 (str): Additional specied ID 2
            notes (str): Additional notes for ambiguity in sample
            image_width_mm (float): Width in mm of the field of view of a single image. Helpful to print a 1mm x 1mm grid to measure
            image_height_mm (float): Height in mm of the field of view of a single image. Helpful to print a 1mm x 1mm grid to measure
            percent_overlap (int, optional): Desired overlap between two images. Defaults to 50.
            x (float, optional): X position of the center of the sample in the gantry coordinate system. Defaults to None.
            y (float, optional): Y position of the center of the sample in the gantry coordinate system. Defaults to None.
            z (float, optional): Z position of the center of the sample in the gantry coordinate system. Defaults to None.
        """
        self.width = cookie_width_mm
        self.height = cookie_height_mm
        self.percent_overlap = percent_overlap
        self._center = (x,y,z)
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
        self.rows, self.cols, self.x_step_size, self.y_step_size = self.calculate_grid()
        self.background = []
        self.background_std = []
        self.coordinates = []
        self.focus_index = []
        self.nvar = []

    def calculate_grid(self):
        """Calculates the amount of rows and columns necessary to traverse the cookie.

        Returns:
            int: Count of rows
            int: Count of cols
            float: step size for translation in x direction 
            float: step size for translation in y direction 
        """
        overlap_x = round(self.image_width_mm * self.percent_overlap / 100, 3)
        overlap_y = round(self.image_height_mm * self.percent_overlap / 100, 3)

        x_step_size = self.image_width_mm - overlap_x
        y_step_size = self.image_height_mm - overlap_y 

        cols = math.ceil(self.width / x_step_size)
        rows = math.ceil(self.height / y_step_size)

        return rows, cols, x_step_size, y_step_size

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
    
