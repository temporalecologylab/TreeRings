import cv2
import logging as log


class Focus:

    def __init__(self):
        # odd numbers only, can be tuned
        self.kernel_size = 5         # Size of the laplacian window
        self.blur_size = 5           # How big of a kernel to use for the gaussian blur

    def focus_thread(self, img_pipeline, directory):
        while True:
            args = img_pipeline.get()
            log.info(args)
            i = args[0]
            j = args[1]
            z = args[2]
            if i == -1:
                img_pipeline.task_done()
                break
            for k in range (0, z):
                imgs = []
                imgs.append(cv2.imread("/{}/frame_{}_{}_{}.jpg".format(directory, i, j, k)))
                log.info("calling focus method")
                focused_image = self.best_focused_image(imgs)
                cv2.imwrite("/{}/focused_images/focused_{}_{}.jpg".format(directory,i,j), focused_image)
            img_pipeline.task_done()
        
    def best_focused_image(self, images):
        best_image = []
        best_lap = 0.0

        for image in images:
            lap = self.compute_laplacian(image)
            if lap.var() > best_lap:
                best_lap = lap.var()
                best_image = image

        return best_image
    
    def compute_laplacian(self,image):

        blurred = cv2.GaussianBlur(image, (self.blur_size,self.blur_size), 0)
        return cv2.Laplacian(blurred, cv2.CV_64F, ksize=self.kernel_size)            
