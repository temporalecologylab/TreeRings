import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GObject, GLib

class VideoSaver:
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

    def start_pipeline(self):
        self.pipeline.set_state(Gst.State.PLAYING)
        print("Pipeline started")

    def stop_pipeline(self):
        self.pipeline.set_state(Gst.State.NULL)
        print("Pipeline stopped")

    def save_frame(self, path):
        self.filesink.set_property("location", path)
        self.filesink.send_event(Gst.Event.new_eos())

    def reset_sink(self):
        # Reset the filesink to not save any more frames
        self.filesink.set_property("location", "/dev/null")
        self.pipeline.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH, 0)
        print("Sink reset")