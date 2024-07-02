from threading import Thread
import logging as log
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GObject, GLib

log.basicConfig(format='%(process)d-%(levelname)s-%(message)s', level=log.INFO)

class Camera:
    def __init__(self):
        Gst.init(None)
        # Create the pipeline with both display and save frame functionality
        self.pipeline = Gst.parse_launch(
            "nvarguscamerasrc ! video/x-raw(memory:NVMM),width=3840,height=2160,framerate=30/1 ! nvvideoconvert flip-method=2 ! tee name=t "
            "t. ! queue ! autovideosink "
            "t. ! queue ! nvjpegenc ! multifilesink name=sink"
        )
        self.filesink = self.pipeline.get_by_name("sink")
        self.filesink.set_property("location", "/dev/null")
        self.filesink.set_property("next-file", 4)  # 4 is the value for "max-size"
        self.filesink.set_property("max-file-size", 1)  # We only want one file

        self.stop_glib = False
        self.glib_thread = Thread(target=self.run_glib)
        self.start_pipeline()

    def run_glib(self):
        loop = GLib.MainLoop()
        GLib.timeout_add_seconds(1, not self.stop_glib)
        try:
            loop.run()
        except KeyboardInterrupt:
            self.stop_glib = True
            loop.quit()

    def start_pipeline(self):
        self.pipeline.set_state(Gst.State.PLAYING)
        self.glib_thread.start()
        log.info("Pipeline started")

    def stop_pipeline(self):
        self.pipeline.set_state(Gst.State.NULL)
        self.stop_glib = True
        self.glib_thread.join()
        log.info("Pipeline stopped")

    def save_frame(self, path):
        self.filesink.set_property("location", path)
        self.filesink.send_event(Gst.Event.new_eos())
        log.info("Saving frame {}".format(path))

    def reset_sink(self):
        # Reset the filesink to not save any more frames
        # TODO: make this a valve that opens and closes to prevent 
        #       needlessly encoding jpeg if we don't want to save frames
        self.filesink.set_property("location", "/dev/null")
        self.pipeline.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH, 0)
        log.info("Sink reset")