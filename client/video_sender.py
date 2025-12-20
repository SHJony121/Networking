"""
Video Sender - Captures and sends video frames via UDP
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2
import time
import socket
import threading
from common.protocol import *

class VideoSender:
    """Captures video and sends it to server via UDP"""
    
    def __init__(self, server_host, server_udp_port, camera_index=0):
        self.server_host = server_host
        self.server_udp_port = server_udp_port
        self.camera_index = camera_index
        
        # Video capture
        self.camera = None
        self.running = False
        self.enabled = True
        
        # UDP socket
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # Current quality settings
        self.current_quality = '360p'
        self.quality_settings = VIDEO_QUALITIES[self.current_quality]
        
        # Frame tracking
        self.frame_id = 0
        self.sequence_num = 0
        
        # Stats
        self.frames_sent = 0
        self.bytes_sent = 0
        self.last_frame_time = 0
        
        # Latest frame for local display
        self.latest_frame = None
        self.frame_lock = threading.Lock()
        
        # Thread
        self.send_thread = None
    
    def start(self):
        """Start video capture and sending"""
        print(f"[VideoSender] Attempting to open camera {self.camera_index}...")
        
        # Use DirectShow backend for better compatibility with virtual cameras (iVCam)
        # CAP_DSHOW works better than default MSMF backend
        self.camera = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
        
        if not self.camera.isOpened():
            print(f"[VideoSender] Failed to open camera {self.camera_index} with DirectShow backend")
            # Try default backend as fallback
            print(f"[VideoSender] Trying default backend...")
            self.camera = cv2.VideoCapture(self.camera_index)
            if not self.camera.isOpened():
                print(f"[VideoSender] Failed to open camera {self.camera_index} with any backend")
                return False
        
        # Test if we can actually read a frame
        ret, test_frame = self.camera.read()
        if not ret or test_frame is None:
            print(f"[VideoSender] Camera {self.camera_index} opened but can't read frames!")
            self.camera.release()
            return False
        
        print(f"[VideoSender] Camera {self.camera_index} opened successfully and tested")
        print(f"[VideoSender] Camera resolution: {int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))}x{int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT))}")
        
        self.running = True
        self.send_thread = threading.Thread(target=self._send_loop, daemon=True)
        self.send_thread.start()
        
        print(f"[VideoSender] Started with quality: {self.current_quality}")
        return True
    
    def stop(self):
        """Stop video capture"""
        self.running = False
        
        if self.send_thread:
            self.send_thread.join(timeout=2)
        
        if self.camera:
            self.camera.release()
        
        print("[VideoSender] Stopped")
    
    def set_enabled(self, enabled):
        """Enable/disable video sending"""
        self.enabled = enabled
    
    def set_quality(self, quality_name):
        """Change video quality"""
        if quality_name in VIDEO_QUALITIES:
            self.current_quality = quality_name
            self.quality_settings = VIDEO_QUALITIES[quality_name]
            print(f"[VideoSender] Quality changed to {quality_name}")
    
    def _send_loop(self):
        """Main sending loop"""
        target_fps = self.quality_settings['fps']
        frame_interval = 1.0 / target_fps
        
        while self.running:
            loop_start = time.time()
            
            if self.enabled:
                self._capture_and_send_frame()
            
            # Maintain target FPS
            elapsed = time.time() - loop_start
            sleep_time = frame_interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)
            
            # Update FPS dynamically
            target_fps = self.quality_settings['fps']
            frame_interval = 1.0 / target_fps
    
    def _capture_and_send_frame(self):
        """Capture and send a single frame"""
        try:
            # Capture frame
            ret, frame = self.camera.read()
            if not ret:
                print("[VideoSender] Failed to read frame from camera")
                return
            
            # Debug: Log first frame capture and check if frame is black
            if self.frames_sent == 0:
                print(f"[VideoSender] First frame captured: {frame.shape}")
                # Check if frame is completely black or nearly black
                mean_brightness = frame.mean()
                print(f"[VideoSender] Frame brightness: {mean_brightness:.2f} (0=black, 255=white)")
                if mean_brightness < 5:
                    print(f"[VideoSender] WARNING: Camera is capturing BLACK frames! Check:")
                    print(f"  1. iVCam app is running on phone")
                    print(f"  2. Camera permissions are granted")
                    print(f"  3. Phone camera is not covered")
                    print(f"  4. Try closing/reopening iVCam app")
            
            # Store original frame for local display
            with self.frame_lock:
                self.latest_frame = frame.copy()
            
            # Resize according to quality settings
            width = self.quality_settings['width']
            height = self.quality_settings['height']
            resized_frame = cv2.resize(frame, (width, height))
            
            # Compress to JPEG
            jpeg_quality = self.quality_settings['jpeg_quality']
            encode_params = [cv2.IMWRITE_JPEG_QUALITY, jpeg_quality]
            _, encoded_frame = cv2.imencode('.jpg', resized_frame, encode_params)
            payload = encoded_frame.tobytes()
            
            # Create packet header
            timestamp = int(time.time() * 1000000)  # microseconds
            header = pack_video_header(
                self.frame_id,
                timestamp,
                self.sequence_num,
                width,
                height,
                len(payload)
            )
            
            # Send packet
            packet = header + payload
            if self.frames_sent == 0:  # Log first packet
                print(f"[VideoSender] Sending first packet to {self.server_host}:{self.server_udp_port}, size={len(packet)} bytes")
            self.socket.sendto(packet, (self.server_host, self.server_udp_port))
            
            # Update counters
            self.frame_id = (self.frame_id + 1) % (2**32)
            self.sequence_num = (self.sequence_num + 1) % (2**32)
            self.frames_sent += 1
            self.bytes_sent += len(packet)
            self.last_frame_time = time.time()
            
            # Debug: Log every 100 frames
            if self.frames_sent % 100 == 0:
                print(f"[VideoSender] {self.frames_sent} frames sent")
        
        except Exception as e:
            print(f"[VideoSender] Error capturing/sending frame: {e}")
            import traceback
            traceback.print_exc()
    
    def get_latest_frame(self):
        """Get the latest captured frame for local display"""
        with self.frame_lock:
            return self.latest_frame.copy() if self.latest_frame is not None else None
    
    def get_stats(self):
        """Get sender statistics"""
        return {
            'frames_sent': self.frames_sent,
            'bytes_sent': self.bytes_sent,
            'current_quality': self.current_quality,
            'fps': self.quality_settings['fps'],
            'resolution': f"{self.quality_settings['width']}x{self.quality_settings['height']}"
        }
    
    def adjust_quality(self, packet_loss, rtt, target_fps=None):
        """
        Adjust video quality based on network conditions
        packet_loss: percentage
        rtt: milliseconds
        """
        quality_levels = ['144p', '240p', '360p', '480p']
        current_index = quality_levels.index(self.current_quality)
        
        # Determine if we should increase or decrease quality
        if packet_loss > PACKET_LOSS_HIGH_THRESHOLD or rtt > RTT_HIGH_THRESHOLD:
            # Network conditions poor - decrease quality
            if current_index > 0:
                new_quality = quality_levels[current_index - 1]
                self.set_quality(new_quality)
                print(f"[VideoSender] Degrading quality due to network: loss={packet_loss}%, rtt={rtt}ms")
        
        elif packet_loss < PACKET_LOSS_LOW_THRESHOLD and rtt < RTT_LOW_THRESHOLD:
            # Network conditions good - increase quality
            if current_index < len(quality_levels) - 1:
                new_quality = quality_levels[current_index + 1]
                self.set_quality(new_quality)
                print(f"[VideoSender] Improving quality: loss={packet_loss}%, rtt={rtt}ms")
        
        # Adjust FPS if specified
        if target_fps:
            self.quality_settings['fps'] = max(5, min(target_fps, 30))
