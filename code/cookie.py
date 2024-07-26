import cv2

class Cookie:
    def __init__(self, cookie_width_mm: int, cookie_height_mm: int, cookie_path: str, species:str, id1:str, id2:str, notes:str, percent_overlap:int = 20, x:float = None, y:float = None, z:float = None):
        self.width = cookie_width_mm
        self.height = cookie_height_mm
        self.percent_overlap = percent_overlap
        self._x = x
        self._y = y
        self._z = z
        self.saturation_max = 0
        self.cookie_path = cookie_path
        self.species = species
        self.id1 = id1
        self.id2 = id2
        self.notes = notes
        self.autoset_sat_min()


    def set_location(self, x, y, z):
        self._x = x
        self._y = y
        self._z = z

    def get_location(self):
        return self._x, self._y, self._z
    
    def autoset_sat_min(self):
        image = cv2.imread(self.cookie_path)
        blurred = cv2.GaussianBlur(image, (777,777), 0)
        image_hsl = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)
        s_channel = image_hsl[:,:,1]
        self.saturation_max = s_channel.max()