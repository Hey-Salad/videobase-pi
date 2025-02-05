import gi
import numpy as np
import gradio as gr
import threading
import logging
from datetime import datetime

# Initialize GStreamer
gi.require_version('Gst', '1.0')
gi.require_version('GstApp', '1.0')
from gi.repository import Gst, GLib

class RTSPViewer:
    def __init__(self, rtsp_url="rtsp://admin:admin@192.168.42.1:554/live"):
        # Set up logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing RTSP Viewer...")
        
        # Initialize GStreamer
        Gst.init(None)
        
        # Create pipeline
        pipeline_str = (
            f'rtspsrc location={rtsp_url} protocols=tcp latency=0 ! '
            'queue ! rtph264depay ! h264parse ! openh264dec ! '
            'videoconvert ! video/x-raw,format=BGR ! '
            'appsink name=sink emit-signals=true max-buffers=1 drop=true'
        )
        
        self.logger.info(f"Creating pipeline: {pipeline_str}")
        self.pipeline = Gst.parse_launch(pipeline_str)
        
        # Get appsink and connect to callback
        self.appsink = self.pipeline.get_by_name('sink')
        self.appsink.connect('new-sample', self.on_new_sample)
        
        # Initialize frame storage
        self.latest_frame = None
        self.frame_count = 0
        self.last_frame_time = datetime.now()
        
        # Add bus watch
        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect('message', self.on_bus_message)
        
        # Start the pipeline
        ret = self.pipeline.set_state(Gst.State.PLAYING)
        if ret == Gst.StateChangeReturn.FAILURE:
            self.logger.error("Failed to start pipeline")
            raise RuntimeError("Failed to start pipeline")
            
        self.logger.info("Pipeline is playing")
        
        # Create GLib main loop
        self.loop = GLib.MainLoop()
        self.loop_thread = threading.Thread(target=self.loop.run)
        self.loop_thread.daemon = True
        self.loop_thread.start()

    def on_bus_message(self, bus, message):
        t = message.type
        if t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            self.logger.error(f"Error: {err}, Debug: {debug}")
        elif t == Gst.MessageType.EOS:
            self.logger.info("End of stream")
        elif t == Gst.MessageType.STATE_CHANGED:
            old_state, new_state, pending_state = message.parse_state_changed()
            self.logger.debug(f"State changed from {old_state} to {new_state}")

    def on_new_sample(self, sink):
        sample = sink.emit('pull-sample')
        if sample:
            buf = sample.get_buffer()
            caps = sample.get_caps()
            
            # Get buffer data
            success, map_info = buf.map(Gst.MapFlags.READ)
            if not success:
                return Gst.FlowReturn.ERROR
                
            # Get dimensions from caps
            caps_struct = caps.get_structure(0)
            height = caps_struct.get_value('height')
            width = caps_struct.get_value('width')
            
            # Create numpy array from buffer data
            frame = np.ndarray(
                shape=(height, width, 3),
                dtype=np.uint8,
                buffer=map_info.data
            ).copy()  # Create a copy of the data
            
            # Unmap buffer
            buf.unmap(map_info)
            
            # Update frame and metrics
            self.latest_frame = frame
            self.frame_count += 1
            
            # Calculate FPS
            current_time = datetime.now()
            time_diff = (current_time - self.last_frame_time).total_seconds()
            fps = 1 / time_diff if time_diff > 0 else 0
            self.last_frame_time = current_time
            
            if self.frame_count % 30 == 0:  # Log FPS every 30 frames
                self.logger.info(f"FPS: {fps:.2f}")
            
            return Gst.FlowReturn.OK
        return Gst.FlowReturn.ERROR

    def get_frame(self):
        if self.latest_frame is not None:
            return self.latest_frame
        return np.zeros((480, 640, 3), dtype=np.uint8)

    def cleanup(self):
        self.logger.info("Cleaning up...")
        if hasattr(self, 'pipeline'):
            self.pipeline.set_state(Gst.State.NULL)
        if hasattr(self, 'loop') and self.loop.is_running():
            self.loop.quit()
        if hasattr(self, 'loop_thread'):
            self.loop_thread.join()
        self.logger.info("Cleanup complete")

def create_gradio_interface():
    # Create RTSP viewer instance
    viewer = RTSPViewer()
    
    def update_frame():
        return viewer.get_frame()
    
    # Create Gradio interface
    with gr.Blocks(
        title="Heysalad ® Videobase Pi",
        css="""
            #header-logo { display: flex; justify-content: center; gap: 20px; align-items: center; margin-bottom: 1em; }
            #header-logo img { height: 60px; width: auto; }
            footer { display: none !important; }
            link[rel="icon"] { content: url("https://raw.githubusercontent.com/Hey-Salad/.github/refs/heads/main/videobase.svg"); }
        """
    ) as interface:
        gr.Markdown(
            """
            <div id="header-logo">
                <img src="https://raw.githubusercontent.com/Hey-Salad/.github/8e1410b012b3601046ded8072317cd99076906f1/Sal.svg" 
                     alt="Heysalad Logo"/>
                <img src="https://raw.githubusercontent.com/Hey-Salad/.github/refs/heads/main/videobase.svg" 
                     alt="Videobase Logo"/>
            </div>
            # Videobase Pi Streamer
            """
        )
        with gr.Row():
            image_output = gr.Image(
                label="Video Feed",
                height=480,
                width=640
            )
        
        interface.load(update_frame, outputs=[image_output])
        
        # Create update interval
        interface.load(
            update_frame,
            outputs=image_output,
            every=0.1  # Update every 100ms
        )
    
    # Launch interface
    interface.queue()
    interface.launch(
        server_name="0.0.0.0",  # Allow external access
        server_port=7860,
        share=False             # Disable public URL sharing
    )
    
    return viewer

if __name__ == "__main__":
    viewer = None
    try:
        viewer = create_gradio_interface()
    except KeyboardInterrupt:
        print("Shutting down...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if viewer:
            viewer.cleanup()