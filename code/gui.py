from tkinter import *
from tkinter import ttk
from tkinter import filedialog
import logging as log

import controller 
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

        ##TODO: make ref to controller when it exists
        self.controller = controller.Controller(3, 2)

        # Frames for entries
        self.frame_entry_cookie = ttk.Frame(self.master, padding = 25)
        self.frame_entry_cookie.grid(column=0, row=0)
        
        self.frame_entry_machine = ttk.Frame(self.master, padding = 25)
        self.frame_entry_machine.grid(column=0, row=1)
        # self.frame_entry.grid_rowconfigure(0, weight=1)
        # self.frame_entry.grid_columnconfigure(0, weight=1)
        # must instantiate controller first\

        # Frames for Buttons
        self.frame_buttons = ttk.Frame(self.master, padding = 25)
        self.frame_buttons.grid()

        self.create_cookie_height_entry()
        self.create_cookie_width_entry()
        self.create_img_height_entry()
        self.create_img_width_entry()
        self.create_percent_overlap_entry()
        self.create_add_cookie_button()
        self.create_directory_button()
        self.create_serial_connect_button()
        self.create_cookie_capture_button()
        self.create_g_code_pause_button()
        self.create_g_code_resume_button()
        self.create_g_code_homing_button()
        self.create_capture_button()
        self.create_arrow_buttons()
        self.create_radio_button_slow_fast()

        #code to properly close windows at end of program
        self.master.protocol("WM_DELETE_WINDOW", self.quit_program)

    def quit_program(self):
        self.controller.quit()
        log.info("Destroy tkinter window")
        self.master.destroy()   

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
        self.contents_height_img.set("2.00")
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

    def create_directory_button(self):
         # Calculate button
        self.button_directory = ttk.Button(self.frame_buttons, text="Select Directory", command=self.request_directory)
        self.button_directory.grid(column = 0, row = 1)

    def create_serial_connect_button(self):
        self.button_serial_connect = ttk.Button(self.frame_buttons, text="Serial Connect", command=self.controller.serial_connect)
        self.button_serial_connect.grid(column = 1, row = 1)

    def create_cookie_capture_button(self):
        self.button_g_code_send = ttk.Button(self.frame_buttons, text="Capture Cookie", command=self.controller.capture_cookie)
        self.button_g_code_send.grid(column = 2, row = 1)

    def create_g_code_pause_button(self):
        self.button_g_code_pause = ttk.Button(self.frame_buttons, text="PAUSE", command=self.controller.cb_pause_g_code)
        self.button_g_code_pause.grid(column = 2, row = 0)

    def create_g_code_resume_button(self):
        self.button_g_code_resume = ttk.Button(self.frame_buttons, text="RESUME", command=self.controller.cb_resume_g_code)
        self.button_g_code_resume.grid(column = 2, row = 2)
    
    def create_g_code_homing_button(self):
        self.button_g_code_homing = ttk.Button(self.frame_buttons, text="SET HOME", command=self.controller.cb_homing_g_code)
        self.button_g_code_homing.grid(column = 2, row = 3)

    def create_capture_button(self):
        self.button_capture = ttk.Button(self.frame_buttons, text="CAPTURE", command=self.controller.cb_capture_image)
        self.button_capture.grid(column = 3, row = 2)


    def create_arrow_buttons(self):
        self.frame_jogging = ttk.Frame(self.master, padding = 25)
        self.frame_jogging.grid()
        self.frame_jogging_title = ttk.Label(self.frame_jogging, text="JOGGING")
        self.button_y_plus = ttk.Button(self.frame_jogging, text="Y+", command=lambda: self.controller.jog_y(self.jog_distance))
        self.button_y_minus = ttk.Button(self.frame_jogging, text="Y-", command=lambda: self.controller.jog_y(-1 * self.jog_distance))
        self.button_x_plus = ttk.Button(self.frame_jogging, text="X+", command=lambda: self.controller.jog_x(self.jog_distance))
        self.button_x_minus = ttk.Button(self.frame_jogging, text="X-", command=lambda: self.controller.jog_x(-1 * self.jog_distance))
        self.button_z_plus = ttk.Button(self.frame_jogging, text="Z+", command=lambda: self.controller.jog_z(self.jog_distance))
        self.button_z_minus = ttk.Button(self.frame_jogging, text="Z-", command=lambda: self.controller.jog_z(-1 * self.jog_distance))
        
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
    
    def create_radio_button_slow_fast(self):
        self.jog_speed = IntVar()
        radio_button_slow = Radiobutton(self.frame_jogging, text="Slow", variable=self.jog_speed, value=1, command=self.cb_speed_switch)
        radio_button_fast = Radiobutton(self.frame_jogging, text="Fast", variable=self.jog_speed, value=2, command=self.cb_speed_switch)

        radio_button_slow.grid(column=5, row=0)
        radio_button_fast.grid(column=5, row=1)
        
    def cb_speed_switch(self):
        speed = self.jog_speed.get()
        self.controller.set_feed_rate(speed)

    def cb_jog_distance(self, event):
        self.jog_distance = float(self.entry_jog_distance.get())

    def request_directory(self):
        directory = filedialog.askdirectory()
        self.controller.set_directory(directory)

    def cb_add_cookie(self):
        width = self.contents_width_cookie.get()
        height = self.contents_height_cookie.get()
        overlap = self.contents_overlap.get()

        self.controller.add_cookie_sample(width, height, overlap)
        log.info("Adding Cookie \nW: {}\nH: {}\nO: {}\n".format(width, height,overlap))

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
               
root = Tk()
myapp = App(root)
# myapp.master.maxsize(1000,500)
myapp.mainloop()
