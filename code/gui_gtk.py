import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gst', '1.0')
from gi.repository import Gtk, Gst, GObject, GLib
import logging as log
import controller
from datetime import datetime

log.basicConfig(format='%(process)d-%(levelname)s-%(message)s', level=log.INFO)

class App(Gtk.Window):
    def __init__(self):
        super().__init__(title="Cookie Capture")
        self.set_default_size(900, 500)
        self.connect("destroy", self.quit_program)
        
        self.controller = controller.Controller(3, 2)

        grid = Gtk.Grid()
        self.add(grid)

        self.create_entries(grid)
        self.create_buttons(grid)
        self.create_jogging_controls(grid)
        
    def quit_program(self, widget):
        self.controller.quit()
        log.info("Destroy GTK window")
        Gtk.main_quit()

    def create_entries(self, grid):
        ## Cookie
        
        frame_entry_cookie = Gtk.Frame(label="Cookie Entries")
        grid.attach(frame_entry_cookie, 0, 0, 1, 1)
        
        box_cookie = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=7)
        frame_entry_cookie.add(box_cookie)
        
        self.create_cookie_height_entry(box_cookie)
        self.create_cookie_width_entry(box_cookie)
        self.create_percent_overlap_entry(box_cookie)
        self.create_species_entries(box_cookie)
        
        ## Machine 
        
        frame_entry_machine = Gtk.Frame(label="Machine Entries")
        grid.attach(frame_entry_machine, 0, 1, 1, 1)
        
        box_machine = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        frame_entry_machine.add(box_machine)
        
        self.create_img_height_entry(box_machine)
        self.create_img_width_entry(box_machine)

    def create_buttons(self, grid):
        frame_buttons = Gtk.Frame(label="Actions")
        grid.attach(frame_buttons, 0, 2, 1, 1)
        
        box_buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        frame_buttons.add(box_buttons)

        self.create_directory_button(box_buttons)
        self.create_serial_connect_button(box_buttons)
        self.create_cookie_capture_button(box_buttons)
        self.create_g_code_capture_all_cookies_button(box_buttons)
        self.create_g_code_resume_button(box_buttons)
        self.create_g_code_homing_button(box_buttons)
        self.create_capture_button(box_buttons)
        self.create_add_cookie_button(box_buttons)
        self.create_test_boundaries_button(box_buttons)

    def create_jogging_controls(self, grid):
        frame_jogging = Gtk.Frame(label="Jogging Controls")
        grid.attach(frame_jogging, 1, 0, 1, 1)
        
        box_jogging = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        frame_jogging.add(box_jogging)

        self.create_arrow_buttons(box_jogging)
        self.create_radio_button_slow_fast(box_jogging)

    def create_cookie_height_entry(self, box):
        label_height_cookie = Gtk.Label(label="Enter Cookie Height (mm):   ")
        box.pack_start(label_height_cookie, True, True, 0)
        self.entry_height_cookie = Gtk.Entry()
        self.entry_height_cookie.set_text("45")
        box.pack_start(self.entry_height_cookie, True, True, 0)
        self.entry_height_cookie.connect('activate', self.print_cookie_height_entry)

    def create_cookie_width_entry(self, box):
        label_width_cookie = Gtk.Label(label="Enter Cookie Width (mm):   ")
        box.pack_start(label_width_cookie, True, True, 0)
        self.entry_width_cookie = Gtk.Entry()
        self.entry_width_cookie.set_text("45")
        box.pack_start(self.entry_width_cookie, True, True, 0)
        self.entry_width_cookie.connect('activate', self.print_cookie_width_entry)

    def create_percent_overlap_entry(self, box):
        label_overlap = Gtk.Label(label="Enter Percent Overlap (%):   ")
        box.pack_start(label_overlap, True, True, 0)
        self.entry_overlap = Gtk.Entry()
        self.entry_overlap.set_text("20")
        box.pack_start(self.entry_overlap, True, True, 0)
        self.entry_overlap.connect('activate', self.print_overlap)
    
    def create_species_entries(self, box):

        label_species = Gtk.Label(label="Enter Species:   ")
        box.pack_start(label_species, True, True, 0)
        self.entry_species = Gtk.Entry()
        self.entry_species.set_text("REQUIRED")
        box.pack_start(self.entry_species, True, True, 0)
        self.entry_species.connect('activate', self.print_species_id)
        
        label_id1 = Gtk.Label(label="Enter ID1:   ")
        box.pack_start(label_id1, True, True, 0)
        self.entry_id1 = Gtk.Entry()
        self.entry_id1.set_text("REQUIRED")
        box.pack_start(self.entry_id1, True, True, 0)
        self.entry_id1.connect('activate', self.print_id1)
        
        label_id2 = Gtk.Label(label="Enter ID2:   ")
        box.pack_start(label_id2, True, True, 0)
        self.entry_id2 = Gtk.Entry()
        self.entry_id2.set_text("REQUIRED")
        box.pack_start(self.entry_id2, True, True, 0)
        self.entry_id2.connect('activate', self.print_id2)
        
        label_notes = Gtk.Label(label="Enter Notes:   ")
        box.pack_start(label_notes, True, True, 0)
        self.entry_notes = Gtk.Entry()
        self.entry_notes.set_text("")
        box.pack_start(self.entry_notes, True, True, 0)
        self.entry_notes.connect('activate', self.print_notes)
        
        
    def create_img_height_entry(self, box):
        label_height_img = Gtk.Label(label="Enter Image Height (mm):   ")
        box.pack_start(label_height_img, True, True, 0)
        self.entry_height_img = Gtk.Entry()
        self.entry_height_img.set_text("2.00")
        box.pack_start(self.entry_height_img, True, True, 0)
        self.entry_height_img.connect('activate', self.print_img_height_entry)

    def create_img_width_entry(self, box):
        label_width_img = Gtk.Label(label="Enter Image Width (mm):   ")
        box.pack_start(label_width_img, True, True, 0)
        self.entry_width_img = Gtk.Entry()
        self.entry_width_img.set_text("3.00")
        box.pack_start(self.entry_width_img, True, True, 0)
        self.entry_width_img.connect('activate', self.print_img_width_entry)

    def create_add_cookie_button(self, box):
        button_calculate = Gtk.Button(label="Add Cookie")
        button_calculate.connect("clicked", self.cb_add_cookie)
        box.pack_start(button_calculate, True, True, 0)

    def create_test_boundaries_button(self, box):
        button_calculate = Gtk.Button(label="Test Cookie Dimensions")
        button_calculate.connect("clicked", self.controller.traverse_cookie_boundary())
        box.pack_start(button_calculate, True, True, 0)

    def create_directory_button(self, box):
        button_directory = Gtk.Button(label="Select Directory")
        button_directory.connect("clicked", self.request_directory)
        box.pack_start(button_directory, True, True, 0)

    def create_serial_connect_button(self, box):
        button_serial_connect = Gtk.Button(label="Serial Connect")
        button_serial_connect.connect("clicked", lambda w: self.controller.serial_connect())
        box.pack_start(button_serial_connect, True, True, 0)

    def create_cookie_capture_button(self, box):
        button_g_code_send = Gtk.Button(label="Capture Cookie")
        button_g_code_send.connect("clicked", lambda w: self.controller.capture_cookie())
        box.pack_start(button_g_code_send, True, True, 0)

    def create_g_code_capture_all_cookies_button(self, box):
        button_g_code_pause = Gtk.Button(label="Capture All Cookies")
        button_g_code_pause.connect("clicked", lambda w: self.controller.capture_all_cookies())
        box.pack_start(button_g_code_pause, True, True, 0)

    def create_g_code_resume_button(self, box):
        button_g_code_resume = Gtk.Button(label="RESUME")
        button_g_code_resume.connect("clicked", lambda w: self.controller.cb_resume_g_code())
        box.pack_start(button_g_code_resume, True, True, 0)

    def create_g_code_homing_button(self, box):
        button_g_code_homing = Gtk.Button(label="SET HOME")
        button_g_code_homing.connect("clicked", lambda w: self.controller.cb_homing_g_code())
        box.pack_start(button_g_code_homing, True, True, 0)

    def create_capture_button(self, box):
        button_capture = Gtk.Button(label="CAPTURE")
        button_capture.connect("clicked", lambda w: self.controller.cb_capture_image())
        box.pack_start(button_capture, True, True, 0)

    def create_arrow_buttons(self, box):
        label_jogging = Gtk.Label(label="Jogging Controls")
        box.pack_start(label_jogging, True, True, 0)

        label_jog_distance = Gtk.Label(label="Enter Jog Distance (mm):   ")
        box.pack_start(label_jog_distance, True, True, 0)
        self.entry_jog_distance = Gtk.Entry()
        self.jog_distance=2.0
        self.entry_jog_distance.set_text("".format(self.jog_distance))
        box.pack_start(self.entry_jog_distance, True, True, 0)
        self.entry_jog_distance.connect('activate', self.cb_jog_distance)

        button_y_plus = Gtk.Button(label="Y+")
        button_y_plus.connect("clicked", lambda w: self.controller.jog_relative_y(self.jog_distance))
        box.pack_start(button_y_plus, True, True, 0)

        button_y_minus = Gtk.Button(label="Y-")
        button_y_minus.connect("clicked", lambda w: self.controller.jog_relative_y(-1 * self.jog_distance))
        box.pack_start(button_y_minus, True, True, 0)

        button_x_plus = Gtk.Button(label="X+")
        button_x_plus.connect("clicked", lambda w: self.controller.jog_relative_x(self.jog_distance))
        box.pack_start(button_x_plus, True, True, 0)

        button_x_minus = Gtk.Button(label="X-")
        button_x_minus.connect("clicked", lambda w: self.controller.jog_relative_x(-1 * self.jog_distance))
        box.pack_start(button_x_minus, True, True, 0)

        button_z_plus = Gtk.Button(label="Z+")
        button_z_plus.connect("clicked", lambda w: self.controller.jog_relative_z(self.jog_distance))
        box.pack_start(button_z_plus, True, True, 0)

        button_z_minus = Gtk.Button(label="Z-")
        button_z_minus.connect("clicked", lambda w: self.controller.jog_relative_z(-1 * self.jog_distance))
        box.pack_start(button_z_minus, True, True, 0)

    def create_radio_button_slow_fast(self, box):
        self.jog_speed = Gtk.RadioButton.new_with_label_from_widget(None, "Slow")
        self.jog_speed.connect("toggled", self.cb_speed_switch, 1)
        box.pack_start(self.jog_speed, True, True, 0)

        radio_button_fast = Gtk.RadioButton.new_with_label_from_widget(self.jog_speed, "Fast")
        radio_button_fast.connect("toggled", self.cb_speed_switch, 2)
        box.pack_start(radio_button_fast, True, True, 0)
        
    def cb_speed_switch(self, button, speed):
        if button.get_active():
            self.controller.set_feed_rate(speed)

    def cb_jog_distance(self, widget):
        self.jog_distance = float(self.entry_jog_distance.get_text())

    def request_directory(self, widget):
        dialog = Gtk.FileChooserDialog(
            title="Please choose a folder", parent=self, action=Gtk.FileChooserAction.SELECT_FOLDER
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN, Gtk.ResponseType.OK
        )

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            self.controller.set_directory(dialog.get_filename())
        dialog.destroy()

    def cb_add_cookie(self, widget):
        width = int(self.entry_width_cookie.get_text())
        height = int(self.entry_height_cookie.get_text())
        overlap = int(self.entry_overlap.get_text())
        species = self.entry_species.get_text()
        id1 = self.entry_id1.get_text()
        id2 = self.entry_id2.get_text()
        notes = self.entry_notes.get_text()
        

        self.controller.add_cookie_sample(width, height, overlap, species, id1, id2, notes)
        log.info("Adding Cookie \nW: {}\nH: {}\nO: {}\nS:  {}\nID1:  {}\nID2:  {}\nNotes:  {}\n".format(width, height, overlap, species, id1, id2, notes))

    def print_cookie_height_entry(self, widget):
        height = int(self.entry_height_cookie.get_text())
        log.info("Update Cookie Height: {} mm".format(height))

    def print_cookie_width_entry(self, widget):
        width = int(self.entry_width_cookie.get_text())
        log.info("Update Cookie Width: {} mm".format(width))

    def print_img_height_entry(self, widget):
        height = float(self.entry_height_img.get_text())
        self.controller.image_height_mm = height
        log.info("Update Image Height: {} mm".format(height))

    def print_img_width_entry(self, widget):
        width = float(self.entry_width_img.get_text())
        self.controller.image_width_mm = width
        log.info("Update Image Width: {} mm".format(width))
    
    def print_overlap(self, widget):
        text = widget.get_text()
        log.info("Percent Overlap: {} %".format(text))
    
    def print_species_id(self, widget):
        text = widget.get_text()
        log.info("Species: {} ".format(text))
    
    def print_id1(self, widget):
        text = widget.get_text()
        log.info("ID1: {} ".format(text))
        
    def print_id2(self, widget):
        text = widget.get_text()
        log.info("ID2: {} ".format(text))

    def print_notes(self, widget):
        text = widget.get_text()
        log.info("Notes: {} ".format(text))
        
        
if __name__ == "__main__":
    #Gst.init(None)
    app = App()
    app.show_all()
    Gtk.main()
