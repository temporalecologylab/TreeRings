# code to take photos when camera has reached the stop position #
import cv2
import time

""" 
gstreamer_pipeline returns a GStreamer pipeline for capturing from the CSI camera
Flip the image by setting the flip_method (most common values: 0 and 2)
display_width and display_height determine the size of each camera pane in the window on the screen
Default 1920x1080 displayd in a 1/4 size window
"""

def gstreamer_pipeline(
    sensor_id=0,
    capture_width=3840,
    capture_height=2160,
    display_width=960,
    display_height=540,
    framerate=5,
    flip_method=0,
):
    return (
        "nvarguscamerasrc sensor-id=%d ! "
        "video/x-raw(memory:NVMM), width=(int)%d, height=(int)%d, framerate=(fraction)%d/1 ! "
        "nvvidconv flip-method=%d ! "
        "video/x-raw, width=(int)%d, height=(int)%d, format=(string)BGRx ! "
        "videoconvert ! "
        "video/x-raw, format=(string)BGR ! appsink"
        % (
            sensor_id,
            capture_width,
            capture_height,
            framerate,
            flip_method,
            display_width,
            display_height,
        )
    )


def show_camera():
    window_title = "CSI Camera"

    # To flip the image, modify the flip_method parameter (0 and 2 are the most common)
    print(gstreamer_pipeline(flip_method=0))
    time.sleep(5)
    capture = cv2.VideoCapture(gstreamer_pipeline(), cv2.CAP_GSTREAMER)
    time.sleep(5)
    
      
    if capture.isOpened():
        try:
            window_handle = cv2.namedWindow(window_title, cv2.WINDOW_AUTOSIZE)
            while True:
                ret,frame = capture.read() 
                if cv2.getWindowProperty(window_title, cv2.WND_PROP_AUTOSIZE) >=0:
                    cv2.imshow(window_title,frame) #display the captured image
                else:
                    break
                if cv2.waitKey(1000) or 0xFF == ord('y'): #save on pressing 'y' 
                    #cv2.imwrite('./images/c1.png',frame)
                    break
        finally:
            capture.release()
            cv2.destroyAllWindows()
    else:
        print("Error: Unable to open camera")

if __name__ == "__main__":
    show_camera()