import cv2
import time
import numpy as np
import math
from pathlib import Path
from datetime import datetime

class Cookie:
    def __init__(self, cookie_width_mm: int, cookie_height_mm: int, species:str, id1:str, id2:str, notes:str, image_width_mm:float, image_height_mm:float, percent_overlap:int = 50, x:float = None, y:float = None, z:float = None):
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
        self.background = np.zeros((self.rows, self.cols))
        self.background_std = np.zeros((self.rows, self.cols))
        self.coordinates = np.zeros((self.rows, self.cols, 3))
        self.focus_index = np.zeros((self.rows, self.cols))
        self.nvar = np.zeros((self.rows, self.cols, 9))

    def calculate_grid(self):
        overlap_x = round(self.image_width_mm * self.percent_overlap / 100, 3)
        overlap_y = round(self.image_height_mm * self.percent_overlap / 100, 3)

        x_step_size = self.image_width_mm - overlap_x
        y_step_size = self.image_height_mm - overlap_y 

        cols = math.ceil(self.width / x_step_size)
        rows = math.ceil(self.height / y_step_size)

        return rows, cols, x_step_size, y_step_size
    
    def set_center_location(self, x, y, z):
        self._center = (x,y,z)

    def set_top_left_location(self, x, y, z):
        self._top_left = (x,y,z)

    def get_center_location(self):
        return self._center
    
    def get_top_left_location(self):
        return self._top_left
    
