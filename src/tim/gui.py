import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gst', '1.0')
from gi.repository import Gtk, Gst, GObject, GLib
from threading import Thread, Event
import logging as log
import controller
from datetime import datetime
import time
import utils

log.basicConfig(format='%(process)d-%(levelname)s-%(message)s', level=log.INFO)

class App(Gtk.Window):
    def __init__(self):
        super().__init__(title="Capture")
        self.config = utils.load_config()

        self.set_default_size(self.config["gui"]["DEFAULT_WINDOW_SIZE"][0], self.config["gui"]["DEFAULT_WINDOW_SIZE"][1])
        self.set_size_request(self.config["gui"]["DEFAULT_WINDOW_SIZE"][0], self.config["gui"]["DEFAULT_WINDOW_SIZE"][1])
        self.connect("destroy", self.quit_program)
        
        self.controller = controller.Controller()

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
        ## Sample
        
        frame_entry_sample = Gtk.Frame(label="Sample Entries")
        frame_entry_sample.set_size_request(-1,-1)
        frame_entry_sample.set_hexpand(True)
        frame_entry_sample.set_vexpand(True)
        frame_entry_sample.set_halign(Gtk.Align.FILL)
        frame_entry_sample.set_valign(Gtk.Align.FILL)
        grid.attach(frame_entry_sample, 1, 0, 1, 1)
        
        box_sample = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=7)
        frame_entry_sample.add(box_sample)
        
        self.create_sample_height_entry(box_sample)
        self.create_sample_width_entry(box_sample)
        
        ## Machine 
        
        frame_entry_machine = Gtk.Frame(label="Machine Entries")
        frame_entry_machine.set_size_request(-1,-1)
        frame_entry_machine.set_hexpand(True)
        frame_entry_machine.set_vexpand(True)
        frame_entry_machine.set_halign(Gtk.Align.FILL)
        frame_entry_machine.set_valign(Gtk.Align.FILL)
        grid.attach(frame_entry_machine, 1, 1, 1, 1)
        
        box_machine = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        frame_entry_machine.add(box_machine)
        
        self.create_zoom_lvl_dropdown(box_machine)
        self.create_img_height_entry(box_machine)
        self.create_img_width_entry(box_machine)

    def create_buttons(self, grid):
        frame_buttons0 = Gtk.Frame(label="Actions")
        frame_buttons0.set_size_request(-1,-1)
        frame_buttons0.set_hexpand(True)
        frame_buttons0.set_vexpand(True)
        frame_buttons0.set_halign(Gtk.Align.FILL)
        frame_buttons0.set_valign(Gtk.Align.FILL)
        grid.attach(frame_buttons0, 0, 0, 1, 1)
        
        box_buttons0 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        frame_buttons0.add(box_buttons0)

        self.create_directory_button(box_buttons0)
        self.create_serial_connect_button(box_buttons0)
        self.create_g_code_homing_button(box_buttons0)
        self.create_capture_button(box_buttons0)
        
        frame_buttons1 = Gtk.Frame()
        frame_buttons1.set_size_request(-1,-1)
        frame_buttons1.set_hexpand(True)
        frame_buttons1.set_vexpand(True)
        frame_buttons1.set_halign(Gtk.Align.FILL)
        frame_buttons1.set_valign(Gtk.Align.FILL)
        grid.attach(frame_buttons1, 0, 1, 1, 1)
        
        box_buttons1 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        frame_buttons1.add(box_buttons1)

        
        self.create_capture_all_samples_button(box_buttons1)
        self.create_add_sample_dialog_button(box_buttons1)
        self.create_test_boundaries_button(box_buttons1)
        self.create_view_added_sample_button(box_buttons1)

    def create_jogging_controls(self, grid):
        frame_jogging = Gtk.Frame(label="Jogging Controls")
        frame_jogging.set_size_request(-1,-1)
        frame_jogging.set_hexpand(True)
        frame_jogging.set_vexpand(True)
        frame_jogging.set_halign(Gtk.Align.FILL)
        frame_jogging.set_valign(Gtk.Align.FILL)
        grid.attach(frame_jogging, 2, 0, 1, 1)
        
        box_jogging = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        frame_jogging.add(box_jogging)

        self.create_jog_buttons(box_jogging)

    def create_sample_height_entry(self, box):
        label_height_sample = Gtk.Label(label="Enter Sample Height (mm):   ")
        box.pack_start(label_height_sample, True, True, 0)
        self.entry_height_sample = Gtk.Entry()
        self.entry_height_sample.set_text("{}".format(self.config["gui"]["DEFAULT_SAMPLE_HEIGHT_MM"]))
        box.pack_start(self.entry_height_sample, True, True, 0)
        self.entry_height_sample.connect('focus-out-event', self.print_sample_height_entry)

    def create_sample_width_entry(self, box):
        label_width_sample = Gtk.Label(label="Enter Sample Width (mm):   ")
        box.pack_start(label_width_sample, True, True, 0)
        self.entry_width_sample = Gtk.Entry()
        self.entry_width_sample.set_text("{}".format(self.config["gui"]["DEFAULT_SAMPLE_WIDTH_MM"]))
        box.pack_start(self.entry_width_sample, True, True, 0)
        self.entry_width_sample.connect('focus-out-event', self.print_sample_width_entry)
    
    def create_zoom_lvl_dropdown(self, box):
        label_zoom_lvl = Gtk.Label(label="Select camera zoom")
        box.pack_start(label_zoom_lvl, True, True, 0)
        
        zoom_liststore = Gtk.ListStore(str)

        zoom_options = ["Custom", "0.7", "1.0", "1.5", "2.0", "2.5", "3.0", "3.5", "4.0", "4.5"]
        for option in zoom_options:
            zoom_liststore.append([option])

        self.zoom_combo = Gtk.ComboBox.new_with_model(zoom_liststore)
        renderer_text = Gtk.CellRendererText()
        self.zoom_combo.pack_start(renderer_text, True)
        self.zoom_combo.add_attribute(renderer_text, "text", 0)

        self.zoom_combo.set_active(self.config["gui"]["DEFAULT_ZOOM_LEVEL"])

        self.zoom_combo.connect("changed", self.on_zoom_combo_changed)

        box.pack_start(self.zoom_combo, True, True, 0)

    def create_img_height_entry(self, box):
        label_height_img = Gtk.Label(label="Enter Image Height (mm):   ")
        box.pack_start(label_height_img, True, True, 0)
        self.entry_height_img = Gtk.Entry()
        self.entry_height_img.set_text("{}".format(3.00))
        box.pack_start(self.entry_height_img, True, True, 0)
        self.entry_height_img.connect('focus-out-event', self.print_img_height_entry)

    def create_img_width_entry(self, box):
        label_width_img = Gtk.Label(label="Enter Image Width (mm):   ")
        box.pack_start(label_width_img, True, True, 0)
        self.entry_width_img = Gtk.Entry()
        self.entry_width_img.set_text("{}".format(5.0))
        box.pack_start(self.entry_width_img, True, True, 0)
        self.entry_width_img.connect('focus-out-event', self.print_img_width_entry)

    def create_add_sample_dialog_button(self, box):
        button_add_dialog = Gtk.Button(label="Add Sample")
        button_add_dialog.connect("clicked", self.cb_add_sample_dialog)
        box.pack_start(button_add_dialog, True, True, 0)

    def create_test_boundaries_button(self, box):
        button_test_dims = Gtk.Button(label="Test Sample Dimensions")
        button_test_dims.connect("clicked", self.cb_traverse_sample)
        box.pack_start(button_test_dims, True, True, 0)

    def create_directory_button(self, box):
        button_directory = Gtk.Button(label="Select Directory")
        button_directory.connect("clicked", self.request_directory)
        box.pack_start(button_directory, True, True, 0)

    def create_serial_connect_button(self, box):
        button_serial_connect = Gtk.Button(label="Serial Connect")
        button_serial_connect.connect("clicked", lambda w: self.controller.serial_connect())
        box.pack_start(button_serial_connect, True, True, 0)

    def create_capture_all_samples_button(self, box):
        button_capture_all_samples = Gtk.Button(label="Capture All Samples")
        button_capture_all_samples.connect("clicked", self.capture_all_samples)
        box.pack_start(button_capture_all_samples, True, True, 0)

    def create_g_code_homing_button(self, box):
        button_g_code_homing = Gtk.Button(label="SET HOME")
        button_g_code_homing.connect("clicked", lambda w: self.controller.cb_homing_g_code())
        box.pack_start(button_g_code_homing, True, True, 0)

    def create_capture_button(self, box):
        button_capture = Gtk.Button(label="Capture Single Image")
        button_capture.connect("clicked", lambda w: self.controller.cb_capture_image())
        box.pack_start(button_capture, True, True, 0)

    def create_view_added_sample_button(self, box):
        button_view_samples = Gtk.Button(label="View Samples Added")
        button_view_samples.connect("clicked", self.view_added_samples)
        box.pack_start(button_view_samples, True, True, 0)

    def create_jog_buttons(self, box):
        label_jogging = Gtk.Label(label="Jogging Controls")
        box.pack_start(label_jogging, True, True, 0)

        label_jog_distance = Gtk.Label(label="Enter Jog Distance (mm):   ")
        box.pack_start(label_jog_distance, True, True, 0)
        self.entry_jog_distance = Gtk.Entry()
        self.jog_distance=2.0
        self.entry_jog_distance.set_text("{}".format(self.jog_distance))
        box.pack_start(self.entry_jog_distance, True, True, 0)
        self.entry_jog_distance.connect('focus-out-event', self.cb_jog_distance)
        
        arrow_grid = Gtk.Grid()
        box.pack_start(arrow_grid, True, True, 0)

        button_y_plus = Gtk.Button(label="Y+")
        button_y_plus.connect("clicked", lambda w: self.controller.jog_relative_y(self.jog_distance))
        arrow_grid.attach(button_y_plus, 2, 0, 1, 1)

        button_y_minus = Gtk.Button(label="Y-")
        button_y_minus.connect("clicked", lambda w: self.controller.jog_relative_y(-1 * self.jog_distance))
        arrow_grid.attach(button_y_minus, 2, 2, 1, 1)

        button_x_plus = Gtk.Button(label="X+")
        button_x_plus.connect("clicked", lambda w: self.controller.jog_relative_x(self.jog_distance))
        arrow_grid.attach(button_x_plus, 3, 1, 1, 1)

        button_x_minus = Gtk.Button(label="X-")
        button_x_minus.connect("clicked", lambda w: self.controller.jog_relative_x(-1 * self.jog_distance))
        arrow_grid.attach(button_x_minus, 1, 1, 1, 1)

        button_z_plus = Gtk.Button(label="Z+")
        button_z_plus.connect("clicked", lambda w: self.controller.jog_relative_z(self.jog_distance))
        arrow_grid.attach(button_z_plus, 4, 0, 1, 1)

        button_z_minus = Gtk.Button(label="Z-")
        button_z_minus.connect("clicked", lambda w: self.controller.jog_relative_z(-1 * self.jog_distance))
        arrow_grid.attach(button_z_minus, 4, 2, 1, 1)
        
        self.jog_speed = Gtk.RadioButton.new_with_label_from_widget(None, "Slow")
        self.jog_speed.connect("toggled", self.cb_speed_switch, 1)
        arrow_grid.attach(self.jog_speed, 0, 0, 1, 1)

        radio_button_fast = Gtk.RadioButton.new_with_label_from_widget(self.jog_speed, "Fast")
        radio_button_fast.connect("toggled", self.cb_speed_switch, 2)
        arrow_grid.attach(radio_button_fast, 0, 2, 1, 1)
        
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

    def cb_traverse_sample(self, widget):
        width = int(self.entry_width_sample.get_text())
        height = int(self.entry_height_sample.get_text())

        self.controller.traverse_sample_boundary(width, height)

    def view_added_samples(self, widget):
        dialog = Gtk.Dialog(title="Added Samples", parent=self, flags=0)
        dialog.add_buttons(Gtk.STOCK_OK, Gtk.ResponseType.OK)
        box = dialog.get_content_area()

        samples = self.controller.get_samples()

        for index, sample in enumerate(samples):
            hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

            entry = Gtk.Entry()
            entry.set_text("{} {} {}".format(sample.species, sample.id1, sample.id2))
            hbox.pack_start(entry, True, True, 0)

            delete_button = Gtk.Button(label="Delete")
            delete_button.connect("clicked", lambda x: samples.pop(index))
            hbox.pack_start(delete_button, True, True, 0)

            box.pack_start(hbox, True, True, 0)
            hbox.show_all()

        dialog.run()
        dialog.destroy()

        self.controller.set_samples(samples)
        
    def capture_all_samples(self, widget):
        dialog = Gtk.Dialog(title="Capturing Samples", parent=self, flags=0)
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL
        )
        
        box = dialog.get_content_area()
        
        self.sample_counter = Gtk.Label(label="Capturing Sample: ")
        self.progressbar = Gtk.ProgressBar()
        self.images_left_label = Gtk.Label(label="Image 1 of ")
        self.time_remaining_label = Gtk.Label(label="Estimated time remaining: calculating...")
        
        box.add(self.sample_counter)
        box.add(self.progressbar)
        box.add(self.images_left_label)
        box.add(self.time_remaining_label)
        
        self.sample_counter.show()
        self.progressbar.show()
        self.images_left_label.show()
        self.time_remaining_label.show()
	
        self.continue_running = True

        stop_capture = Event()
        
        def on_response(dialog, response_id):
            if response_id == Gtk.ResponseType.CANCEL:
                self.continue_running = False
                stop_capture.set()
            dialog.destroy()
            
        dialog.connect("response", on_response)
        dialog.show_all()

        capture_thread = Thread(target=self.controller.capture_all_samples, args = (self.update_progress, stop_capture))
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
            sample_name = value[2]
            GLib.idle_add(self.sample_counter.set_text, "Capturing Sample: {}".format(sample_name))
            GLib.idle_add(self.images_left_label.set_text, "Image 1 of ")
            GLib.idle_add(self.time_remaining_label.set_text, "Estimated time remaining: calculating...")
            GLib.idle_add(self.progressbar.set_fraction, 0)
        else:
            elapsed_time, img_num, total_imgs = value
            fraction = img_num/total_imgs
            estimated_total_time = elapsed_time * total_imgs
            remaining_time = estimated_total_time - (elapsed_time * img_num)
            remaining_hours = int(remaining_time/3600)
            remaining_minutes = int(remaining_time%3600 / 60)
            # remaining_seconds = int(remaining_time % 60)
            remaining_time_text = "Estimated time remaining: {} hr {} min".format(remaining_hours, remaining_minutes)
            image_left_text = "Image {} of {}".format(img_num, total_imgs)
            GLib.idle_add(self.images_left_label.set_text, image_left_text)
            GLib.idle_add(self.time_remaining_label.set_text, remaining_time_text)
            GLib.idle_add(self.progressbar.set_fraction, fraction)

    def cb_add_sample_dialog(self, widget):
        width = int(self.entry_width_sample.get_text())
        height = int(self.entry_height_sample.get_text())
        overlap, species, id1, id2, notes, is_core = self.show_metadata_dialog()
        if species == False:
            return
        if overlap == '':
            overlap = 50
        else:
            overlap = float(overlap)
            species = species.replace(" ", "_")
            id1 = id1.replace(" ", "_")
            id2 = id2.replace(" ", "_")
        self.controller.add_sample(width, height, overlap, species, id1, id2, notes, is_core)
        log.info("Adding Sample \nW: {}\nH: {}\nO: {}\nS:  {}\nID1:  {}\nID2:  {}\nNotes:  {}\n".format(width, height, overlap, species, id1, id2, notes))
    
    def show_metadata_dialog(self):
        dialog = Gtk.Dialog(title="Add Sample", parent=self, flags=0)
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
        is_core_button = Gtk.CheckButton(label = "Core Sample")
        
        #Create larger text box for notes 
        text_view = Gtk.TextView()
        text_view.set_wrap_mode(Gtk.WrapMode.WORD)
        text_view.set_size_request(300,200)

        notes_window = Gtk.ScrolledWindow()
        notes_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        notes_window.add(text_view)

        box.add(species_label)
        box.add(species_entry)
        box.add(id1_label)
        box.add(id1_entry)
        box.add(id2_label)
        box.add(id2_entry)
        box.add(overlap_label)
        box.add(overlap_entry)
        box.add(notes_label)
        box.add(notes_window)
        box.add(is_core_button)

        species_label.show()
        species_entry.show()
        id1_label.show()
        id1_entry.show()
        id2_label.show()
        id2_entry.show()
        overlap_label.show()
        overlap_entry.show()
        notes_label.show()
        notes_window.show_all()
        is_core_button.show()

        overlap_entry.set_text("{}".format(self.config["gui"]["DEFAULT_PERCENT_OVERLAP"]))
        is_core_button.set_active(True) #default to core
        # Run the dialog and capture the response
        response = dialog.run()

        if response == Gtk.ResponseType.OK:
            overlap = overlap_entry.get_text()
            species = species_entry.get_text()
            id1 = id1_entry.get_text()
            id2 = id2_entry.get_text()
            buffer = text_view.get_buffer()
            notes = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), True)
            is_core = is_core_button.get_active()
            log.info("Adding Sample")
        else:
            overlap = False
            species = False
            id1 =  False
            id2 = False
            notes = False
            is_core = False
            log.info("Cancel Sample Add")

        dialog.destroy()
        return overlap, species, id1, id2, notes, is_core
    
    def on_zoom_combo_changed(self, combo):
        zoom_size_dict = {
            "0.7": [10.0,18.0],
            "1.0": [6.0,11.0],
            "1.5": [4.5,7.8],
            "2.0": [3.0,5.3],
            "2.5": [3.0, 5.0],
            "3.0": [2.2,4.0],
            "3.5": [2.0,3.5],
            "4.0": [2.0,3.0],
            "4.5": [1.5, 3.0]
        }
        tree_iter = combo.get_active_iter()
        if tree_iter is not None:
            model = combo.get_model()
            option = model[tree_iter][0]
            if option != "Custom":
                height, width = zoom_size_dict[option]
                self.entry_height_img.set_text(str(height))
                self.controller.set_image_height_mm(height)
                self.entry_width_img.set_text(str(width))
                self.controller.set_image_width_mm(width)

    def print_sample_height_entry(self, widget, event):
        height = int(self.entry_height_sample.get_text())
        log.info("Update Sample Height: {} mm".format(height))

    def print_sample_width_entry(self, widget, event):
        width = int(self.entry_width_sample.get_text())
        log.info("Update Sample Width: {} mm".format(width))

    def print_img_height_entry(self, widget, event):
        height = float(self.entry_height_img.get_text())
        self.controller.image_height_mm = height
        self.zoom_combo.set_active(0)
        log.info("Update Image Height: {} mm".format(height))

    def print_img_width_entry(self, widget, event):
        width = float(self.entry_width_img.get_text())
        self.controller.image_width_mm = width
        self.zoom_combo.set_active(0)
        log.info("Update Image Width: {} mm".format(width))        
        
if __name__ == "__main__":
    #Gst.init(None)
    app = App()
    app.show_all()
    Gtk.main()
