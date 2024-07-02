class Cookie:
    def __init__(self, cookie_width_mm: int, cookie_height_mm: int, percent_overlap:int = 20):
        self.width = cookie_width_mm
        self.height = cookie_height_mm
        self.percent_overlap = percent_overlap
        self.start_point = (None, None)

    def set_location(self, top_left: tuple[int, int]):
        self.start_point = top_left
