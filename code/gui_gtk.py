import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gst', '1.0')
from gi.repository import Gtk, Gst, GObject, GLib
from threading import Thread
import logging as log
import controller
from datetime import datetime
import time

log.basicConfig(format='%(process)d-%(levelname)s-%(message)s', level=log.INFO)

class App(Gtk.Window):
    def __init__(self):
        super().__init__(title="Cookie Capture")
        self.set_default_size(600, 400)
        self.set_size_request(-1,-1)
        self.connect("destroy", self.quit_program)
        
        self.controller = controller.Controller(3, 2)

        grid = Gtk.Grid()
        grid.set_row_homogeneous(False)
        grid.set_column_homogeneous(False)
        
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
        frame_entry_cookie.set_size_request(-1,-1)
        frame_entry_cookie.set_hexpand(True)
        frame_entry_cookie.set_vexpand(True)
        frame_entry_cookie.set_halign(Gtk.Align.FILL)
        frame_entry_cookie.set_valign(Gtk.Align.FILL)
        grid.attach(frame_entry_cookie, 0, 0, 1, 1)
        
        box_cookie = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=7)
        frame_entry_cookie.add(box_cookie)
        
        self.create_cookie_height_entry(box_cookie)
        self.create_cookie_width_entry(box_cookie)
        
        ## Machine 
        
        frame_entry_machine = Gtk.Frame(label="Machine Entries")
        frame_entry_machine.set_size_request(-1,-1)
        frame_entry_machine.set_hexpand(True)
        frame_entry_machine.set_vexpand(True)
        frame_entry_machine.set_halign(Gtk.Align.FILL)
        frame_entry_machine.set_valign(Gtk.Align.FILL)
        grid.attach(frame_entry_machine, 0, 1, 1, 1)
        
        box_machine = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        frame_entry_machine.add(box_machine)
        
        self.create_img_height_entry(box_machine)
        self.create_img_width_entry(box_machine)

    def create_buttons(self, grid):
        frame_buttons = Gtk.Frame(label="Actions")
        frame_buttons.set_size_request(-1,-1)
        frame_buttons.set_hexpand(True)
        frame_buttons.set_vexpand(True)
        frame_buttons.set_halign(Gtk.Align.FILL)
        frame_buttons.set_valign(Gtk.Align.FILL)
        grid.attach(frame_buttons, 0, 2, 1, 1)
        
        box_buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        frame_buttons.add(box_buttons)

        self.create_directory_button(box_buttons)
        self.create_serial_connect_button(box_buttons)
        self.create_capture_all_cookies_button(box_buttons)
        self.create_g_code_resume_button(box_buttons)
        self.create_g_code_homing_button(box_buttons)
        self.create_capture_button(box_buttons)
        self.create_add_cookie_dialog_button(box_buttons)
        self.create_test_boundaries_button(box_buttons)
        self.create_view_added_cookies_button(box_buttons)

    def create_jogging_controls(self, grid):
        frame_jogging = Gtk.Frame(label="Jogging Controls")
        frame_jogging.set_size_request(-1,-1)
        frame_jogging.set_hexpand(True)
        frame_jogging.set_vexpand(True)
        frame_jogging.set_halign(Gtk.Align.FILL)
        frame_jogging.set_valign(Gtk.Align.FILL)
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
        self.entry_height_cookie.connect('focus-out-event', self.print_cookie_height_entry)

    def create_cookie_width_entry(self, box):
        label_width_cookie = Gtk.Label(label="Enter Cookie Width (mm):   ")
        box.pack_start(label_width_cookie, True, True, 0)
        self.entry_width_cookie = Gtk.Entry()
        self.entry_width_cookie.set_text("45")
        box.pack_start(self.entry_width_cookie, True, True, 0)
        self.entry_width_cookie.connect('focus-out-event', self.print_cookie_width_entry)
    
    def create_img_height_entry(self, box):
        label_height_img = Gtk.Label(label="Enter Image Height (mm):   ")
        box.pack_start(label_height_img, True, True, 0)
        self.entry_height_img = Gtk.Entry()
        self.entry_height_img.set_text("2.00")
        box.pack_start(self.entry_height_img, True, True, 0)
        self.entry_height_img.connect('focus-out-event', self.print_img_height_entry)

    def create_img_width_entry(self, box):
        label_width_img = Gtk.Label(label="Enter Image Width (mm):   ")
        box.pack_start(label_width_img, True, True, 0)
        self.entry_width_img = Gtk.Entry()
        self.entry_width_img.set_text("3.00")
        box.pack_start(self.entry_width_img, True, True, 0)
        self.entry_width_img.connect('focus-out-event', self.print_img_width_entry)

    def create_add_cookie_dialog_button(self, box):
        button_add_dialog = Gtk.Button(label="Add Cookie")
        button_add_dialog.connect("clicked", self.cb_add_cookie_dialog)
        box.pack_start(button_add_dialog, True, True, 0)

    def create_test_boundaries_button(self, box):
        button_test_dims = Gtk.Button(label="Test Cookie Dimensions")
        button_test_dims.connect("clicked", self.cb_traverse_cookie)
        box.pack_start(button_test_dims, True, True, 0)

    def create_directory_button(self, box):
        button_directory = Gtk.Button(label="Select Directory")
        button_directory.connect("clicked", self.request_directory)
        box.pack_start(button_directory, True, True, 0)

    def create_serial_connect_button(self, box):
        button_serial_connect = Gtk.Button(label="Serial Connect")
        button_serial_connect.connect("clicked", lambda w: self.controller.serial_connect())
        box.pack_start(button_serial_connect, True, True, 0)

    def create_capture_all_cookies_button(self, box):
        button_capture_all_cookies = Gtk.Button(label="Capture All Cookies")
        button_capture_all_cookies.connect("clicked", self.capture_all_cookies)
        box.pack_start(button_capture_all_cookies, True, True, 0)

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

    def create_view_added_cookies_button(self, box):
        button_view_cookies = Gtk.Button(label="View Cookies Added")
        button_view_cookies.connect("clicked", self.view_added_cookies)
        box.pack_start(button_view_cookies, True, True, 0)

    def create_arrow_buttons(self, box):
        label_jogging = Gtk.Label(label="Jogging Controls")
        box.pack_start(label_jogging, True, True, 0)

        label_jog_distance = Gtk.Label(label="Enter Jog Distance (mm):   ")
        box.pack_start(label_jog_distance, True, True, 0)
        self.entry_jog_distance = Gtk.Entry()
        self.jog_distance=2.0
        self.entry_jog_distance.set_text("".format(self.jog_distance))
        box.pack_start(self.entry_jog_distance, True, True, 0)
        self.entry_jog_distance.connect('focus-out-event', self.cb_jog_distance)

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

    def cb_jog_distance(self, widget, event):
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

    def cb_traverse_cookie(self, widget):
        width = int(self.entry_width_cookie.get_text())
        height = int(self.entry_height_cookie.get_text())

        self.controller.traverse_cookie_boundary(width, height)

    def view_added_cookies(self, widget):
        dialog = Gtk.Dialog(title="Added Cookies", parent=self, flags=0)
        dialog.add_buttons(Gtk.STOCK_OK, Gtk.ResponseType.OK)
        box = dialog.get_content_area()

        cookies = self.controller.get_cookies()

        for index, cookie in enumerate(cookies)
            hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

            entry = Gtk.Entry()
            entry.set_text("{} {} {}".format(cookie.species, cookie.id1, cookie.id2))
            hbox.pack_start(entry, True, True, 0)

            delete_button = Gtk.Button(label="Delete")
            delete_button.connect("clicked", lambda x: cookies.pop(index))
            hbox.pack_start(delete_button, True, True, 0)

            box.pack_start(hbox, True, True, 0)
            hbox.show_all()

        dialog.run()
        dialog.destroy()

        self.controller.set_cookies(cookies)
        
    def capture_all_cookies(self, widget):
        dialog = Gtk.Dialog(title="Capturing Cookies", parent=self, flags=0)
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL
        )
        
        box = dialog.get_content_area()
        
        self.cookie_counter = Gtk.Label(label="Capturing Cookie: ")
        self.progressbar = Gtk.ProgressBar()
        self.images_left_label = Gtk.Label(label="Image 1 of ")
        self.time_remaining_label = Gtk.Label(label="Estimated time remaining: calculating...")
        
        box.add(self.cookie_counter)
        box.add(self.progressbar)
        box.add(self.images_left_label)
        box.add(self.time_remaining_label)
        
        self.cookie_counter.show()
        self.progressbar.show()
        self.images_left_label.show()
        self.time_remaining_label.show()
	
        self.continue_running = True
        
        def on_response(dialog, response_id):
            if response_id == Gtk.ResponseType.CANCEL:
                self.continue_running = False
            dialog.destroy()
            
        dialog.connect("response", on_response)
        dialog.show_all()
        
        capture_thread = Thread(target=self.controller.capture_all_cookies, args = (self.update_progress, ))
        capture_thread.start()
   	
        def update_progress_bar():
            if self.continue_running:
                return True
            else:
                capture_thread.join()
                return False
        
        GLib.timeout_add(100, update_progress_bar)

        dialog.run()
        capture_thread.join()
        GLib.idle_add(dialog.destroy)
            
        
    def update_progress(self, value):
        if value[0] == True:
            cookie_name = value[2]
            GLib.idle_add(self.cookie_counter.set_text, "Capturing Cookie: {}".format(cookie_name))
            GLib.idle_add(self.images_left_label.set_text, "Image 1 of ")
            GLib.idle_add(self.time_remaining_label.set_text, "Estimated time remaining: calculating...")
            GLib.idle_add(self.progressbar.set_fraction, 0)
        else:
            elapsed_time, img_num, total_imgs = value
            fraction = img_num/total_imgs
            estimated_total_time = elapsed_time * total_imgs
            remaining_time = estimated_total_time - (elapsed_time * img_num)
            remaining_minutes = int(remaining_time/60)
            remaining_seconds = int(remaining_time % 60)
            remaining_time_text = "Estimated time remaining: {}min {}sec".format(remaining_minutes, remaining_seconds)
            image_left_text = "Image {} of {}".format(img_num, total_imgs)
            GLib.idle_add(self.images_left_label.set_text, image_left_text)
            GLib.idle_add(self.time_remaining_label.set_text, remaining_time_text)
            GLib.idle_add(self.progressbar.set_fraction, fraction)

    def cb_add_cookie_dialog(self, widget):
        width = int(self.entry_width_cookie.get_text())
        height = int(self.entry_height_cookie.get_text())
        overlap, species, id1, id2, notes = self.show_metadata_dialog()
        log.info(species)
        log.info(id1)
        log.info(id2)
        log.info(notes)
        if species == False:
            return
        if overlap == '':
            overlap = 50
        else:
            overlap = float(overlap)
        self.controller.add_cookie_sample(width, height, overlap, species, id1, id2, notes)
        log.info("Adding Cookie \nW: {}\nH: {}\nO: {}\nS:  {}\nID1:  {}\nID2:  {}\nNotes:  {}\n".format(width, height, overlap, species, id1, id2, notes))
    
    def show_metadata_dialog(self):
        dialog = Gtk.Dialog(title="Add Cookie", parent=self, flags=0)
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OK, Gtk.ResponseType.OK
        )

        # Add required entries
        box = dialog.get_content_area()
        overlap_label = Gtk.Label(label="Image Overlap (%)")
        overlap_entry = Gtk.Entry()
        species_label = Gtk.Label(label="Species")
        species_entry = Gtk.Entry()
        id1_label = Gtk.Label(label="ID 1")
        id1_entry = Gtk.Entry()
        id2_label = Gtk.Label(label="ID 2")
        id2_entry = Gtk.Entry()
        notes_label = Gtk.Label(label="Notes")
        
        #Create larger text box for notes 
        text_view = Gtk.TextView()
        text_view.set_wrap_mode(Gtk.WrapMode.WORD)
        text_view.set_size_request(300,200)

        notes_window = Gtk.ScrolledWindow()
        notes_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        notes_window.add(text_view)

        box.add(overlap_label)
        box.add(overlap_entry)
        box.add(species_label)
        box.add(species_entry)
        box.add(id1_label)
        box.add(id1_entry)
        box.add(id2_label)
        box.add(id2_entry)
        box.add(notes_label)
        box.add(notes_window)

        overlap_label.show()
        overlap_entry.show()
        species_label.show()
        species_entry.show()
        id1_label.show()
        id1_entry.show()
        id2_label.show()
        id2_entry.show()
        notes_label.show()
        notes_window.show_all()

        # Run the dialog and capture the response
        response = dialog.run()

        if response == Gtk.ResponseType.OK:
            overlap = overlap_entry.get_text()
            species = species_entry.get_text()
            id1 = id1_entry.get_text()
            id2 = id2_entry.get_text()
            buffer = text_view.get_buffer()
            notes = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), True)
            log.info("Adding Cookie")
        else:
            overlap = False
            species = False
            id1 =  False
            id2 = False
            notes = False
            log.info("Cancel Cookie Add")

        dialog.destroy()
        return overlap, species, id1, id2, notes
        

    def print_cookie_height_entry(self, widget, event):
        height = int(self.entry_height_cookie.get_text())
        log.info("Update Cookie Height: {} mm".format(height))

    def print_cookie_width_entry(self, widget, event):
        width = int(self.entry_width_cookie.get_text())
        log.info("Update Cookie Width: {} mm".format(width))

    def print_img_height_entry(self, widget, event):
        height = float(self.entry_height_img.get_text())
        self.controller.image_height_mm = height
        log.info("Update Image Height: {} mm".format(height))

    def print_img_width_entry(self, widget, event):
        width = float(self.entry_width_img.get_text())
        self.controller.image_width_mm = width
        log.info("Update Image Width: {} mm".format(width))        
        
if __name__ == "__main__":
    #Gst.init(None)
    app = App()
    app.show_all()
    Gtk.main()
