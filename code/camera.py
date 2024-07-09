from threading import Thread
import time
import logging as log
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GObject, GLib

log.basicConfig(format='%(process)d-%(levelname)s-%(message)s', level=log.INFO)

class Camera:
    def __init__(self, quiet = True):
        Gst.init(None)
        # Create the pipeline with both display and save frame functionality
        self.pipeline = Gst.parse_launch(
            "nvarguscamerasrc wbmode=1 ee-mode=2 ee-strength=0.75 exposurecompensation=0.25 wbmode=1 ee-mode=2 ee-strength=0.75 exposurecompensation=0.25 ! video/x-raw(memory:NVMM),width=3840,height=2160,framerate=30/1 ! "
            ""
            "nvvideoconvert flip-method=2 ! videobalance contrast=1.25 ! tee name=t "
            "t. ! queue ! autovideosink "
            #"t. ! queue leaky=1 max-size-buffers=1 name=q ! avenc_tiff ! filesink name=sink async=false"
        )

        self.bus = self.pipeline.get_bus()

        if quiet:
            pass
        else:
            self.bus.add_signal_watch()
            self.bus.connect("message", self.on_bus_message)

        # Get the tee element from the pipeline
        self.t = self.pipeline.get_by_name("t")

        # Storage for all the save bins, needs timestamp when added 
        self.bins = []
        self.bins_creation_times = []
        
        self.stop_thread = False
        thread = Thread(target=self.bin_cleanup_thread)
        thread.start()
        self.start_pipeline()

    def on_bus_message(self, bus, message):
        if message.type == Gst.MessageType.EOS:
            print("End-of-stream")
            self.stop_pipeline()
        elif message.type == Gst.MessageType.ERROR:
            err, debug_info = message.parse_error()
            print(f"Error received from element {message.src.get_name()}: {err.message}")
            print(f"Debugging information: {debug_info}")
            self.stop_pipeline()
        elif message.type == Gst.MessageType.WARNING:
            err, debug_info = message.parse_warning()
            print(f"Warning received from element {message.src.get_name()}: {err.message}")
            print(f"Debugging information: {debug_info}")
        elif message.type == Gst.MessageType.STATE_CHANGED:
            old_state, new_state, pending_state = message.parse_state_changed()
            print(f"Element {message.src.get_name()} changed state from {old_state.value_nick} to {new_state.value_nick}")
        elif message.type == Gst.MessageType.INFO:
            info, debug_info = message.parse_info()
            print(f"Info received from element {message.src.get_name()}: {info.message}")
            print(f"Debugging information: {debug_info}")
        elif message.type == Gst.MessageType.BUFFERING:
            percent = message.parse_buffering()
            print(f"Buffering {percent}%")
        elif message.type == Gst.MessageType.CLOCK_LOST:
            print("Clock lost, restoring pipeline state")
            self.pipeline.set_state(Gst.State.PAUSED)
            self.pipeline.set_state(Gst.State.PLAYING)
        elif message.type == Gst.MessageType.STREAM_STATUS:
            type, owner = message.parse_stream_status()
            print(f"Stream status: {type.value_nick} for {owner.get_name()}")
        elif message.type == Gst.MessageType.ELEMENT:
            # Handle custom element messages
            structure = message.get_structure()
            if structure:
                print(f"Element message from {message.src.get_name()}: {structure.to_string()}")
        else:
            print(f"Unexpected message received: {message.type}")

    def bin_cleanup_thread(self):
        # Let the bins exist for a predetermined amount of time, remove all bins that have existed for longer than this amount
        save_time_ms = 100

        while not self.stop_thread:
            if len(self.bins) > 0:
                bin_creation_time_ms = self.bins_creation_times[0] * 1000.0

                time_now_ms = round(time.time() * 1000.0)
                criteria = time_now_ms - save_time_ms
                # remove the bin if it's been longer than the save time
                while bin_creation_time_ms < criteria:
                    log.info("Removing bin, {} < {}".format(bin_creation_time_ms, criteria))
                    bin = self.bins.pop(0)
                    self.bins_creation_times.pop(0)
                    self.remove_save_bin(bin)
                    
                    if len(self.bins) > 0:
                    	# does the next item in the list satisfy the criteria as well? Repeat if so
                        bin_creation_time_ms = self.bins_creation_times[0] * 1000.0 
                    else:
                        break
            time.sleep(0.5)

    def create_save_bin(self, path="./test.tiff"):
        log.info("Creating save bin")
        bin_description = "queue name=q ! avenc_tiff name=encoder ! filesink name=filesink async=false location={}".format(path)
        save_bin = Gst.parse_bin_from_description(bin_description, True)

        return save_bin
    
    def remove_save_bin(self, bin):
        log.info("Selecting save bin GhostPad")
        ghostpad = bin.get_static_pad("sink")

        log.info("Selecting Tee-Pad (Peer of GhostPad)")
        teepad = ghostpad.get_peer()

        def blocking_pad_probe(pad, info):
            log.info("Stopping Bin")
            log.debug(bin.set_state(Gst.State.NULL))

            log.info("Removing Bin from Pipeline")
            log.debug(self.pipeline.remove(bin))

            log.info("Releasing Tee-Pad")
            log.debug(self.t.release_request_pad(teepad))

            log.info("Removed Save Bin from")

            return Gst.PadProbeReturn.REMOVE    

        log.info("Configuring blocking probe on teepad")
        teepad.add_probe(Gst.PadProbeType.BLOCK, blocking_pad_probe)

    def queue_full_callback(self, queue):
        log.info("\nQUEUE OVERRUN\n")
    
    def start_pipeline(self):
        self.pipeline.set_state(Gst.State.PLAYING)
        log.info("Pipeline started")

    def stop_pipeline(self):
        self.pipeline.set_state(Gst.State.NULL)
        self.stop_thread = True
        log.info("Pipeline stopped")

    def save_frame(self, path):
        log.info("Saving frame {}".format(path))
        bin = self.create_save_bin(path)
        self.bins.append(bin)
        self.bins_creation_times.append(time.time())
        
        log.info("Adding save bin to pipeline")
        self.pipeline.add(bin)

        log.info("Syncing save bin to parent state")
        bin.sync_state_with_parent()
        
        log.info("Linking tee to save bin")
        self.t.link(bin)

    def reset_sink(self):
        # Reset the filesink to not save any more frames
        # TODO: make this a valve that opens and closes to prevent 
        #       needlessly encoding jpeg if we don't want to save frames
        self.filesink.set_property("location", "/dev/null")
        self.pipeline.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH, 0)
        log.info("Sink reset")

