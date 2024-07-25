class Cookie:
    def __init__(self, cookie_width_mm: int, cookie_height_mm: int, species:str, id1:str, id2:str, notes:str, percent_overlap:int = 20, x:float = None, y:float = None, z:float = None):
        self.width = cookie_width_mm
        self.height = cookie_height_mm
        self.percent_overlap = percent_overlap
        self._x = x
        self._y = y
        self._z = z
        self.species = species
        self.id1 = id1
        self.id2 = id2
        self.notes = notes

    def set_location(self, x, y, z):
        self._x = x
        self._y = y
        self._z = z

    def get_location(self):
        return self._x, self._y, self._z