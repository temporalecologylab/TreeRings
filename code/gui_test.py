from tkinter import *
from tkinter import ttk
from tkinter import filedialog
import logging as log
import cv2

from threading import Thread

import GCodeManager 
import time
from datetime import datetime

log.basicConfig(format='%(process)d-%(levelname)s-%(message)s', level=log.INFO)


class App(Frame):
    def __init__(self, master):
        super().__init__(master)
        # self.grid()
        self.master = master
        self.master.geometry("900x500")
        self.master.title("Cookie Capture")
        self.master.grid_rowconfigure(0, weight=1)
        self.master.grid_columnconfigure(0, weight=1)

        self.controller = GCodeManager.MachineControl(3, 2)

        self.PAUSED = False
        self.SAVEFLAG = False #TODO: make this mutex

        # Frames for entries
        self.frame_entry_cookie = ttk.Frame(self.master, padding = 25)
        self.frame_entry_cookie.grid(column=0, row=0)
        
        self.frame_entry_machine = ttk.Frame(self.master, padding = 25)
        self.frame_entry_machine.grid(column=0, row=1)
        # self.frame_entry.grid_rowconfigure(0, weight=1)
        # self.frame_entry.grid_columnconfigure(0, weight=1)
        # must instantiate controller first

        self.create_cookie_height_entry()
        self.create_cookie_width_entry()
        self.create_img_height_entry()
        self.create_img_width_entry()
        self.create_percent_overlap_entry()
        self.create_add_cookie_button()
        self.create_calculate_grid_button()
        self.create_directory_button()
        self.calculate_grid() # must run before create_serial_connect_button()
        self.create_serial_connect_button()
        self.create_g_code_sender_button()
        self.create_g_code_pause_button()
        self.create_g_code_resume_button()
        self.create_g_code_homing_button()
        self.create_capture_button()
        self.create_arrow_buttons()

        img_window = Thread(target=self.start_image_preview)
        img_window.start()


    def create_cookie_height_entry(self):
        # Entry for cookie height
        self.label_height_cookie = ttk.Label(self.frame_entry_cookie, text="Enter Cookie Height (mm):   ")
        self.label_height_cookie.grid(column = 0, row = 0)
        self.entry_height_cookie = Entry(self.frame_entry_cookie)
        self.entry_height_cookie.grid(column = 1, row = 0)

        ## Create the application variable.
        self.contents_height_cookie = IntVar()
        ## Set it to some value.
        self.contents_height_cookie.set("45")
        ## Tell the entry widget to watch this variable.
        self.entry_height_cookie["textvariable"] = self.contents_height_cookie

        ## Define a callback for when the user hits return.
        ## It prints the current value of the variable.
        self.entry_height_cookie.bind('<Key-Return>',
                             self.print_cookie_height_entry)

    def create_cookie_width_entry(self):
        # Entry for cookie width
        self.label_width_cookie = ttk.Label(self.frame_entry_cookie, text="Enter Cookie Width (mm):   ")
        self.label_width_cookie.grid(column = 3, row = 0)
        self.entry_width_cookie = Entry(self.frame_entry_cookie)
        self.entry_width_cookie.grid(column = 4, row = 0)

        ## Create the application variable.
        self.contents_width_cookie = IntVar()
        ## Set it to some value.
        self.contents_width_cookie.set("45")
        ## Tell the entry widget to watch this variable.
        self.entry_width_cookie["textvariable"] = self.contents_width_cookie

        ## Define a callback for when the user hits return.
        ## It prints the current value of the variable.
        self.entry_width_cookie.bind('<Key-Return>',
                             self.print_cookie_width_entry)

    def create_percent_overlap_entry(self):
        # Entry for percent overlap between images
        self.label_overlap = ttk.Label(self.frame_entry_cookie, text="Enter Percent Overlap (%):   ")
        self.label_overlap.grid(column = 0, row = 2)
        self.entry_overlap = Entry(self.frame_entry_cookie)
        self.entry_overlap.grid(column = 1, row = 2)

        ## Create the application variable.
        self.contents_overlap = IntVar()
        ## Set it to some value.
        self.contents_overlap.set("20")
        ## Tell the entry widget to watch this variable.
        self.entry_overlap["textvariable"] = self.contents_overlap

        self.entry_overlap.bind('<Key-Return>',
                             self.print_overlap)
        
    def create_add_cookie_button(self):
        self.button_calculate = ttk.Button(self.frame_entry_cookie, text="Add Cookie", command=self.cb_add_cookie)
        self.button_calculate.grid(column = 4, row = 2)

    def create_img_height_entry(self):
        # Entry for Image height
        self.label_height_img = ttk.Label(self.frame_entry_machine, text="Enter Image Height (mm):   ")
        self.label_height_img.grid(column = 0, row = 1)
        self.entry_height_img = Entry(self.frame_entry_machine)
        self.entry_height_img.grid(column = 1, row = 1)

        ## Create the application variable.
        self.contents_height_img = DoubleVar()
        ## Set it to some value.
        self.contents_height_img.set("2.25")
        ## Tell the entry widget to watch this variable.
        self.entry_height_img["textvariable"] = self.contents_height_img

        ## Define a callback for when the user hits return.
        ## It prints the current value of the variable.
        self.entry_height_img.bind('<Key-Return>',
                             self.print_img_height_entry)
        
    def create_img_width_entry(self):
        # Entry for Image width
        self.label_width_img = ttk.Label(self.frame_entry_machine, text="Enter Image Width (mm):   ")
        self.label_width_img.grid(column = 3, row = 1)
        self.entry_width_img = Entry(self.frame_entry_machine)
        self.entry_width_img.grid(column = 4, row = 1)

        ## Create the application variable.
        self.contents_width_img = DoubleVar()
        ## Set it to some value.
        self.contents_width_img.set("3.00")
        ## Tell the entry widget to watch this variable.
        self.entry_width_img["textvariable"] = self.contents_width_img

        ## Define a callback for when the user hits return.
        ## It prints the current value of the variable.
        self.entry_width_img.bind('<Key-Return>',
                             self.print_img_width_entry)

    def create_calculate_grid_button(self):
         # Calculate button
        self.frame_buttons = ttk.Frame(self.master, padding = 25)
        self.frame_buttons.grid()
        self.button_calculate = ttk.Button(self.frame_buttons, text="Calculate Grid", command=self.calculate_grid)
        self.button_calculate.grid(column = 1, row = 1)

    def create_directory_button(self):
         # Calculate button
        self.button_directory = ttk.Button(self.frame_buttons, text="Select Directory", command=self.request_directory)
        self.button_directory.grid(column = 0, row = 1)

    def create_serial_connect_button(self):
        self.button_serial_connect = ttk.Button(self.frame_buttons, text="Serial Connect", command=self.controller.serial_connect_port)
        self.button_serial_connect.grid(column = 2, row = 1)

    def create_g_code_sender_button(self):
        self.button_g_code_send = ttk.Button(self.frame_buttons, text="Send G Code", command=self.bulk_send_g_code)
        self.button_g_code_send.grid(column = 3, row = 1)

    def create_g_code_pause_button(self):
        self.button_g_code_pause = ttk.Button(self.frame_buttons, text="PAUSE", command=self.cb_pause_g_code)
        self.button_g_code_pause.grid(column = 3, row = 0)

    def create_g_code_resume_button(self):
        self.button_g_code_resume = ttk.Button(self.frame_buttons, text="RESUME", command=self.cb_resume_g_code)
        self.button_g_code_resume.grid(column = 3, row = 2)
    
    def create_g_code_homing_button(self):
        self.button_g_code_homing = ttk.Button(self.frame_buttons, text="SET HOME", command=self.cb_homing_g_code)
        self.button_g_code_homing.grid(column = 3, row = 3)

    def create_capture_button(self):
        self.button_capture = ttk.Button(self.frame_buttons, text="CAPTURE", command=self.cb_capture_image)
        self.button_capture.grid(column = 4, row = 2)


    def create_arrow_buttons(self):
        self.frame_jogging = ttk.Frame(self.master, padding = 25)
        self.frame_jogging.grid()
        self.frame_jogging_title = ttk.Label(self.frame_jogging, text="JOGGING")
        self.button_y_plus = ttk.Button(self.frame_jogging, text="Y+", command=self.jog_y_plus)
        self.button_y_minus = ttk.Button(self.frame_jogging, text="Y-", command=self.jog_y_minus)
        self.button_x_plus = ttk.Button(self.frame_jogging, text="X+", command=self.jog_x_plus)
        self.button_x_minus = ttk.Button(self.frame_jogging, text="X-", command=self.jog_x_minus)
        self.button_z_plus = ttk.Button(self.frame_jogging, text="Z+", command=self.jog_z_plus)
        self.button_z_minus = ttk.Button(self.frame_jogging, text="Z-", command=self.jog_z_minus)
        
        # Entry for percent overlap between images
        self.label_jog_distance = ttk.Label(self.frame_jogging, text="Enter Jog Distance (mm):   ")
        self.label_jog_distance.grid(column = 2, row = 0)
        self.entry_jog_distance = Entry(self.frame_jogging)
        self.entry_jog_distance.grid(column = 3, row = 0)

        ## Create the application variable.
        self.contents_jog_distance = DoubleVar()
        ## Set it to some value.
        self.jog_distance = 2.0
        self.contents_jog_distance.set("{}".format(self.jog_distance))
        ## Tell the entry widget to watch this variable.
        self.entry_jog_distance["textvariable"] = self.contents_jog_distance

        self.entry_jog_distance.bind('<Key-Return>',
                             self.cb_jog_distance)


        self.frame_jogging_title.grid(column=0, row = 0)
        self.button_y_plus.grid(column = 2, row = 1)
        self.button_y_minus.grid(column = 2, row = 3)
        self.button_x_plus.grid(column = 3, row = 2)
        self.button_x_minus.grid(column = 1, row = 2)
        self.button_z_plus.grid(column = 4, row = 1)
        self.button_z_minus.grid(column = 4, row = 3)

    def start_image_preview(self):
        while True:
            img = self.controller.capture_image()
            img = cv2.flip(img, 2)
            cv2.imshow("window", img)

            time.sleep(.2)
            cv2.waitKey(1)
            
    def jog_y_plus(self):
        log.info("jog +{} mm y".format(self.jog_distance))
        self.controller.jog_y(self.jog_distance)

    def jog_y_minus(self):
        log.info("jog -{} mm y".format(self.jog_distance))
        self.controller.jog_y(self.jog_distance * -1)
    
    def jog_x_plus(self):
        log.info("jog +{} mm x".format(self.jog_distance))
        self.controller.jog_x(self.jog_distance)

    def jog_x_minus(self):
        log.info("jog -{} mm x".format(self.jog_distance))
        self.controller.jog_x(self.jog_distance * -1)
    
    def jog_z_plus(self):
        log.info("jog +{} mm z".format(self.jog_distance))
        self.controller.jog_z(self.jog_distance)

    def jog_z_minus(self):
        log.info("jog -{} mm z".format(self.jog_distance))
        self.controller.jog_z(self.jog_distance * -1)

    def cb_jog_distance(self, event):
        self.jog_distance = float(self.entry_jog_distance.get())

    def request_directory(self):
        self.directory = filedialog.askdirectory()
    
    def cb_pause_g_code(self):
        self.controller.pause()

    def cb_resume_g_code(self):
        self.controller.resume()

    def cb_homing_g_code(self):
        self.controller.homing_sequence()

    def cb_add_cookie(self):
        width = self.contents_width_cookie.get()
        height = self.contents_height_cookie.get()
        overlap = self.contents_overlap.get()

        self.controller.add_cookie_sample(width, height, overlap)
        log.info("Adding Cookie \nW: {}\nH: {}\nO: {}\n".format(width, height,overlap))

    def cb_capture_image(self):
        img = self.controller.capture_image()
        name = "image_{}.jpg".format(datetime.now().strftime("%H_%M_%S"))
        cv2.imwrite(name, img)
        log.info("Saving {}".format(name))

    def print_cookie_height_entry(self, event):
        try:
            height = self.contents_height_cookie.get()
            log.info("Update Image Height: {} mm".format(height))
        except TclError:
            self.entry_height_cookie.delete(0, END)
            log.info("Enter a double")

    def print_cookie_width_entry(self, event):
        try:
            width = self.contents_width_cookie.get()
            log.info("Update Cookie Width: {} mm".format(width))
        except TclError:
            self.entry_width_cookie.delete(0, END)
            log.info("Enter a double")
    
    def print_img_height_entry(self, event):
        try:
            height = self.contents_height_img.get()
            self.controller.image_height_mm = height
            log.info("Update Image Height: {} mm".format(height))
        except TclError:
            self.entry_height_img.delete(0, END)
            log.info("Enter a double")
    
    def print_img_width_entry(self, event):
        try:
            width = self.contents_width_img.get()
            self.controller.image_width_mm = width
            log.info("Update Image Width: {} mm".format(width))
        except TclError:
            self.entry_width_img.delete(0, END)
            log.info("Enter a double")
    
    
    def print_overlap(self, event):
        try:
            log.info("Image Overlap: {} %".format(self.contents_overlap.get()))
        except TclError:
            self.entry_overlap.delete(0, END)
            log.info("Enter an integer")

    def calculate_grid(self): 
        if len(self.controller.cookie_samples) > 0:
            self.g_code = self.controller.generate_serpentine(self.controller.cookie_samples[-1]) #TODO make work with multiple samples... will be hard
            log.info("{} overlapping images calculated".format(len(self.g_code)))
        else:
            log.info("ERROR: NO COOKIES ADDED... Add a cookie using the button")
        

    def bulk_send_g_code(self, pause = 1):
        log.info("Starting serpentine")

        self.controller.send_serpentine(self.g_code)
            

   
root = Tk()
myapp = App(root)
# myapp.master.maxsize(1000,500)
myapp.mainloop()