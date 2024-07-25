from threading import Thread
import time
import logging as log
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GObject, GLib

log.basicConfig(format='%(process)d-%(levelname)s-%(message)s', level=log.INFO)

class Camera:

    def __init__(self, quiet = True):
        # Adding hardcoded image size, will need to update to update DPI
        W_PIXELS = 3840
        H_PIXELS = 2160

        Gst.init(None)
        # Create the pipeline with both display and save frame functionality
        
        self.pipeline = Gst.parse_launch(
            "nvarguscamerasrc wbmode=1 ee-mode=2 ee-strength=0.5 exposurecompensation=0.5 exposuretimerange='680000000 600000000'  aelock=true ! video/x-raw(memory:NVMM),width={},height={},framerate=30/1 ! videorate ! video/x-raw(memory:NVMM),width=3840,height=2160,framerate=15/1 !".format(W_PIXELS, H_PIXELS)                         #683709000
            "nvvideoconvert flip-method=2 ! videobalance contrast=1.25 ! tee name=t "
            "t. ! queue ! autovideosink "
            #"t. ! fakesink "
            "t. ! queue max-size-buffers=10 leaky=2 ! avenc_tiff name=encoder ! tee name=t_bin ! fakesink"
        )

        self.quiet = quiet
        self.bus = self.pipeline.get_bus()
        self.w_pixels = W_PIXELS
        self.h_pixels = H_PIXELS

        if quiet:
            pass
        else:
            self.bus.add_signal_watch()
            self.bus.connect("message", self.on_bus_message)

        # Get the tee element from the pipeline
        self.t = self.pipeline.get_by_name("t_bin")

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
                    if not self.quiet:
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
        #log.info("Creating save bin")
        bin_description = "queue name=q{} leaky=1 ! filesink name=filesink async=false location={}".format(path,path)
        save_bin = Gst.parse_bin_from_description(bin_description, True)

        # Add a flag to track buffer
        save_bin.buffer_seen = False
        queue = save_bin.get_by_name("q{}".format(path))
        queue.get_static_pad("sink").add_probe(Gst.PadProbeType.BUFFER, self.drop_all_but_first_buffer_probe(save_bin))

        return save_bin
    
    def drop_all_but_first_buffer_probe(self, save_bin):
        def probe(pad, info):
            if save_bin.buffer_seen:
                return Gst.PadProbeReturn.DROP
            save_bin.buffer_seen = True
            return Gst.PadProbeReturn.OK
        return probe

    def remove_save_bin(self, bin):
        #log.info("Selecting save bin GhostPad")
        ghostpad = bin.get_static_pad("sink")

        #log.info("Selecting Tee-Pad (Peer of GhostPad)")
        teepad = ghostpad.get_peer()

        def blocking_pad_probe(pad, info):
            #log.info("Stopping Bin")
            bin.set_state(Gst.State.NULL)

            #log.info("Removing Bin from Pipeline")
            self.pipeline.remove(bin)

            #log.info("Releasing Tee-Pad")
            if teepad and teepad.get_parent() == self.t:
                self.t.release_request_pad(teepad)
            else:
                log.error("Pad parent mismatch or teepad is None")
                
            #log.info("Removed Save Bin from")

            return Gst.PadProbeReturn.REMOVE    

        #log.info("Configuring blocking probe on teepad")
        if teepad is not None:
            teepad.add_probe(Gst.PadProbeType.BLOCK, blocking_pad_probe)
        else:
            del bin
            
        #hopefully gets rid of memory problems. Sometimes the teepad does not get the blocking probe to remove
        #time.sleep(1)
        #del bin

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
        if not self.quiet:
            log.info("Saving frame {}".format(path))
        bin = self.create_save_bin(path)
        self.bins.append(bin)
        self.bins_creation_times.append(time.time())
        
        #log.info("Adding save bin to pipeline")
        self.pipeline.add(bin)

        #log.info("Syncing save bin to parent state")
        bin.sync_state_with_parent()
        
        #log.info("Linking tee to save bin")
        self.t.link(bin)
