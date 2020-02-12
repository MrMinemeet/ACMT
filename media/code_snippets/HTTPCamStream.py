#!/usr/bin/python3

# Script sends Pi Camera Image to http://{IP}:5000/stream.mjpeg
# picamera pacage required!
# pip3 install picamera

import io, socketserver, picamera
from threading import Condition
from http import server


# --- SETTINGS ---
PORT = 5000
RESOLUTION = '1280x720' # e.g 1920x1080, 1280x720, ...
FPS = 30
ROTATION = 180  # no rotation --> 0





class streamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True

class streamingOutput(object):
    def __init__(self):
        self.frame = None
        self.buffer = io.BytesIO()
        self.condition = Condition()

    def write(self, buf):
        if buf.startswith(b'\xff\xd8'):
            # New frame available to get to buffer --> Notify all clients
            self.buffer.truncate()
            with self.condition:
                self.frame = self.buffer.getvalue()
                self.condition.notify_all()
            self.buffer.seek(0)
        return self.buffer.write(buf)

class streamingHandler(server.BaseHTTPRequestHandler):
    def do_GET(self):
        # Check if user is requesting stream
        if self.path == '/stream.mjpg':
            # yes --> Send Stream
            # send header for beginning streaming
            self.send_response(200) # HTTP OK
            self.send_header('Age', 0)
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
            self.end_headers()

            # start Stream
            try:
                while True:
                    # Send new image when available
                    with output.condition:
                        output.condition.wait()
                        frame = output.frame
                    # Header for sending image
                    self.wfile.write(b'--FRAME\r\n')
                    self.send_header('Content-Type', 'image/jpeg')
                    self.send_header('Content-Length', len(frame))
                    self.end_headers()
                    self.wfile.write(frame)
                    self.wfile.write(b'\r\n')
            except Exception as e:
                print('Removed streaming client %s: %s', self.client_address, str(e))
        else:
            # User requested something else --> Send 404 Page
            self.send_error(404)
            self.end_headers()

# --- MAIN ---
#Only resolution and framerate in Constructorparameters
with picamera.PiCamera(resolution=RESOLUTION, framerate=FPS) as cam:
    output = streamingOutput()
    # Rotation if needed
    cam.rotation = ROTATION
    #start stream
    cam.start_recording(output, format='mjpeg')

    try:
        #IP, Port
        hostAndPort = ('',PORT) # '' as IP automatically get's ip
        server = streamingServer(hostAndPort, streamingHandler)
        server.serve_forever() # Serves as long as script is running
    finally:
        cam.stop_recording() # Stops stream to make camera accessable from other apps again