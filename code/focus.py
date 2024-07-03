import cv2
import logging as log

log.basicConfig(format='%(process)d-%(levelname)s-%(message)s', level=log.INFO)

class Focus:

    def __init__(self):
        # odd numbers only, can be tuned
        self.kernel_size = 5         # Size of the laplacian window
        self.blur_size = 5           # How big of a kernel to use for the gaussian blur

    def find_focus(self, img_pipeline, directory):
        while True:
            image_files = img_pipeline.get()
            log.info("Images For focus finding: {}".format(image_files))
            if image_files == [-1]:
                img_pipeline.task_done()
                break
                      
            image_name = image_files[1].split("/")[-1]
            extract_row = image_name[6]
            extract_col = image_name[8]
            filename = "focused_{}_{}.jpg".format(extract_row, extract_col) 
            focused_image = self.best_focused_image(image_files)
            cv2.imwrite("{}/focused_images/{}".format(directory,filename), focused_image)
            img_pipeline.task_done()
        
    def best_focused_image(self, images):
        best_image = []
        best_lap = 0.0

        for image_name in images:
            image = cv2.imread(image_name)
            lap = self.compute_laplacian(image)
            if lap.var() > best_lap:
                best_lap = lap.var()
                best_image = image

        return best_image
    
    def compute_laplacian(self,image):

        blurred = cv2.GaussianBlur(image, (self.blur_size,self.blur_size), 0)
        return cv2.Laplacian(blurred, cv2.CV_64F, ksize=self.kernel_size)            
