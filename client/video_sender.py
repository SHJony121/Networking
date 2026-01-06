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
import mss
import numpy as np
from common.protocol import *

class VideoSender:
    """Captures video and sends it to server via UDP"""
    
    def __init__(self, server_host, server_udp_port, camera_index=0, simulated_loss_rate=0.0):
        self.server_host = server_host
        self.server_udp_port = server_udp_port
        self.camera_index = camera_index
        self.simulated_loss_rate = simulated_loss_rate
        
        # Video capture
        self.camera = None
        self.running = False
        self.enabled = True
        self.sct_instance = None
        
        # Screen capture
        self.is_screen_sharing = False
        
        # UDP socket
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # Current quality settings
        self.current_quality = '360p'
        self.quality_settings = VIDEO_QUALITIES[self.current_quality]
        self.quality_callback = None # Callback for quality changes
        
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
            
            # Notify listener
            if self.quality_callback:
                try:
                    self.quality_callback(quality_name)
                except Exception as e:
                    print(f"[VideoSender] Error in quality callback: {e}")

    def set_screen_sharing(self, enabled):
        """Toggle screen sharing mode"""
        self.is_screen_sharing = enabled
        print(f"[VideoSender] Screen sharing set to: {enabled}")
    
    def _send_loop(self):
        """Main sending loop"""
        target_fps = self.quality_settings['fps']
        frame_interval = 1.0 / target_fps
        
        # Initialize mss here (in the thread) for safety and performance
        with mss.mss() as sct:
            self.sct_instance = sct
            
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
                
        self.sct_instance = None # Cleanup

    def _capture_and_send_frame(self):
        """Capture and send a single frame"""
        try:
            frame = None
            
            if self.is_screen_sharing:
                # Capture screen using the thread-local instance
                try:
                    sct = self.sct_instance
                    if not sct:
                         # Should not happen given the context manager in loop
                         return

                    # monitor 1 is usually the main monitor
                    if len(sct.monitors) > 1:
                        monitor = sct.monitors[1]
                    else:
                         monitor = sct.monitors[0] # Fallback
                    
                    screenshot = sct.grab(monitor)
                    
                    # Convert to numpy array (BGRA)
                    frame = np.array(screenshot)
                    
                    if self.frames_sent % 30 == 0: # Log more often for debug
                        print(f"[VideoSender] Screen capture size: {frame.shape}")
                        
                    # Drop alpha channel (BGRA -> BGR)
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                except Exception as sct_e:
                    print(f"[VideoSender] Screen share error: {sct_e}")
                    self.is_screen_sharing = False # Fallback
                    return
                
            else:
                # Capture camera
                if self.camera:
                    ret, cam_frame = self.camera.read()
                    if ret:
                        frame = cam_frame
                    else:
                        print("[VideoSender] Failed to read frame from camera")
                        return

            if frame is None:
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
            
            # Simulate packet loss
            should_send = True
            if self.simulated_loss_rate > 0:
                import random
                if random.uniform(0, 100) < self.simulated_loss_rate:
                    should_send = False
            
            if should_send:
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
        User Rules:
        > 15% loss -> 144p
        > 10% loss -> 240p
        > 2%  loss -> 360p
        <= 2% loss -> 480p
        """
        # Determine target quality based on strict thresholds
        target_quality = '480p' # Default best
        
        if packet_loss > 15:
            target_quality = '144p'
        elif packet_loss > 10:
            target_quality = '240p'
        elif packet_loss > 2:
            target_quality = '360p'
        else:
            # Loss is low (<= 2%), but check Latency
            # If ping is extremely high (>400ms), don't force 480p
            if rtt > 400:
                target_quality = '360p'
            else:
                target_quality = '480p'
        
        # Apply change if different
        if self.current_quality != target_quality:
            print(f"[VideoSender] Adapting quality: {self.current_quality} -> {target_quality} (Loss={packet_loss:.1f}%, RTT={rtt:.0f}ms)")
            self.set_quality(target_quality)
    
        # Adjust FPS if specified
        if target_fps:
            self.quality_settings['fps'] = max(5, min(target_fps, 30))
