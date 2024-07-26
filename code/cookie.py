import cv2

class Cookie:
    def __init__(self, cookie_width_mm: int, cookie_height_mm: int, species:str, id1:str, id2:str, notes:str, cookie_path:str, percent_overlap:int = 20, x:float = None, y:float = None, z:float = None, x_tl:float = None, y_tl:float = None, z_tl:float = None):
        self.width = cookie_width_mm
        self.height = cookie_height_mm
        self.percent_overlap = percent_overlap
        self._center = (x,y,z)
        self._top_left = (x_tl, y_tl, z_tl)
        self.species = species
        self.id1 = id1
        self.id2 = id2
        self.notes = notes
        self.cookie_path = cookie_path
        self.autoset_sat_min()


    def set_center_location(self, x, y, z):
        self._center = (x,y,z)

    def set_top_left_location(self, x, y, z):
        self._top_left = (x,y,z)

    def get_center_location(self):
        return self._center
    
    def get_top_left_location(self):
        return self._top_left
    
    def autoset_sat_min(self):
        image = cv2.imread(self.cookie_path)
        blurred = cv2.GaussianBlur(image, (777,777), 0)
        image_hsl = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)
        s_channel = image_hsl[:,:,1]
        self.saturation_max = s_channel.max()