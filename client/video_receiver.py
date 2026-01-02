"""
Video Receiver - Receives and displays video frames via UDP
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2
import numpy as np
import time
import socket
import threading
from collections import deque
from common.protocol import *

class VideoReceiver:
    """Receives video frames via UDP"""
    
    def __init__(self, local_udp_port):
        self.local_udp_port = local_udp_port
        
        # UDP socket
        self.socket = None
        self.running = False
        
        # Frame buffer (for handling out-of-order packets)
        self.frame_buffer = {}  # {frame_id: (frame_data, timestamp)}
        self.latest_frame = None
        self.latest_frame_lock = threading.Lock()
        
        # Per-sender frame storage: {sender_addr: latest_frame}
        self.sender_frames = {}
        self.sender_frames_lock = threading.Lock()
        
        # Stats tracking
        self.frames_received = 0
        self.bytes_received = 0
        self.frames_lost = 0
        
        # Per-sender sequence tracking to properly calculate packet loss
        # {sender_addr: last_sequence_num}
        self.sender_sequence = {}
        
        # Jitter calculation
        self.arrival_times = deque(maxlen=100)
        self.jitter = 0
        
        # Frame timing
        self.frame_timestamps = deque(maxlen=100)
        self.fps_received = 0
        
        # Thread
        self.receive_thread = None
    
    def start(self):
        """Start receiving video"""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(('0.0.0.0', self.local_udp_port))
        
        # Get the actual port if 0 was specified (OS-assigned)
        if self.local_udp_port == 0:
            self.local_udp_port = self.socket.getsockname()[1]
        
        self.running = True
        self.receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
        self.receive_thread.start()
        
        print(f"[VideoReceiver] Started on port {self.local_udp_port}")
        return True
    
    def stop(self):
        """Stop receiving video"""
        self.running = False
        
        if self.receive_thread:
            self.receive_thread.join(timeout=2)
        
        if self.socket:
            self.socket.close()
        
        print("[VideoReceiver] Stopped")
    
    def _receive_loop(self):
        """Main receiving loop"""
        self.socket.settimeout(0.1)
        
        received_count = 0
        while self.running:
            try:
                data, addr = self.socket.recvfrom(65535)
                received_count += 1
                if received_count % 100 == 0:  # Log every 100 packets
                    print(f"[VideoReceiver] Received {received_count} packets, latest from {addr}")
                self._process_packet(data, addr)
            
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"[VideoReceiver] Error receiving: {e}")
    
    def _process_packet(self, data, addr):
        """Process received video packet"""
        try:
            # Parse header
            if len(data) < VIDEO_HEADER_SIZE:
                return
            
            header = unpack_video_header(data)
            payload = data[VIDEO_HEADER_SIZE:]
            
            # Check for lost frames - track per sender to avoid false positives
            # when receiving interleaved packets from multiple senders
            sender_key = addr  # Use sender address as key
            last_seq = self.sender_sequence.get(sender_key, -1)
            
            if last_seq != -1:
                expected_seq = (last_seq + 1) % (2**32)
                if header['sequence_num'] != expected_seq:
                    # Only count as loss if sequence jumped forward (not backward/duplicate)
                    seq_diff = (header['sequence_num'] - expected_seq) % (2**32)
                    if seq_diff < 1000:  # Reasonable gap (not wraparound)
                        self.frames_lost += seq_diff
            
            self.sender_sequence[sender_key] = header['sequence_num']
            
            # Record arrival time for jitter calculation
            arrival_time = time.time()
            self.arrival_times.append(arrival_time)
            
            # Calculate jitter
            if len(self.arrival_times) >= 2:
                diffs = [self.arrival_times[i] - self.arrival_times[i-1] 
                        for i in range(1, len(self.arrival_times))]
                if diffs:
                    mean_diff = sum(diffs) / len(diffs)
                    variance = sum((d - mean_diff) ** 2 for d in diffs) / len(diffs)
                    self.jitter = variance ** 0.5 * 1000  # Convert to ms
            
            # Decode JPEG frame
            frame = cv2.imdecode(np.frombuffer(payload, dtype=np.uint8), cv2.IMREAD_COLOR)
            
            if frame is not None:
                # Update latest frame (backward compatibility)
                with self.latest_frame_lock:
                    self.latest_frame = frame
                
                # Store frame per sender
                with self.sender_frames_lock:
                    self.sender_frames[addr] = frame
                
                # Update stats
                self.frames_received += 1
                self.bytes_received += len(data)
                self.frame_timestamps.append(time.time())
                
                # Calculate received FPS
                if len(self.frame_timestamps) >= 2:
                    time_span = self.frame_timestamps[-1] - self.frame_timestamps[0]
                    if time_span > 0:
                        self.fps_received = (len(self.frame_timestamps) - 1) / time_span
        
        except Exception as e:
            print(f"[VideoReceiver] Error processing packet: {e}")
    
    def get_latest_frame(self):
        """Get the most recent frame (thread-safe)"""
        with self.latest_frame_lock:
            return self.latest_frame
    
    def get_all_sender_frames(self):
        """Get frames from all senders: returns {addr: frame}"""
        with self.sender_frames_lock:
            return dict(self.sender_frames)  # Return a copy
        with self.latest_frame_lock:
            return self.latest_frame.copy() if self.latest_frame is not None else None
    
    def get_stats(self):
        """Get receiver statistics"""
        total_expected = self.frames_received + self.frames_lost
        packet_loss_pct = (self.frames_lost / total_expected * 100) if total_expected > 0 else 0
        
        return {
            'frames_received': self.frames_received,
            'bytes_received': self.bytes_received,
            'frames_lost': self.frames_lost,
            'packet_loss_percent': packet_loss_pct,
            'jitter_ms': self.jitter,
            'fps_received': self.fps_received
        }
    
    def calculate_rtt(self, send_timestamp_us):
        """
        Calculate RTT given sender's timestamp
        Returns: RTT in milliseconds
        """
        current_time_us = int(time.time() * 1000000)
        rtt_us = current_time_us - send_timestamp_us
        return rtt_us / 1000.0  # Convert to ms

class MultiVideoReceiver:
    """Manages multiple video streams (one per participant)"""
    
    def __init__(self, base_udp_port):
        self.base_udp_port = base_udp_port
        self.receivers = {}  # {participant_id: VideoReceiver}
        self.receiver_lock = threading.Lock()
    
    def add_participant(self, participant_id):
        """Add a new participant video stream"""
        with self.receiver_lock:
            if participant_id not in self.receivers:
                # Each participant gets their own port (simplified)
                port = self.base_udp_port + len(self.receivers)
                receiver = VideoReceiver(port)
                receiver.start()
                self.receivers[participant_id] = receiver
                print(f"[MultiVideoReceiver] Added participant {participant_id} on port {port}")
    
    def remove_participant(self, participant_id):
        """Remove a participant video stream"""
        with self.receiver_lock:
            if participant_id in self.receivers:
                self.receivers[participant_id].stop()
                del self.receivers[participant_id]
                print(f"[MultiVideoReceiver] Removed participant {participant_id}")
    
    def get_frame(self, participant_id):
        """Get latest frame from a participant"""
        with self.receiver_lock:
            receiver = self.receivers.get(participant_id)
            if receiver:
                return receiver.get_latest_frame()
            return None
    
    def get_all_frames(self):
        """Get latest frames from all participants"""
        with self.receiver_lock:
            frames = {}
            for participant_id, receiver in self.receivers.items():
                frame = receiver.get_latest_frame()
                if frame is not None:
                    frames[participant_id] = frame
            return frames
    
    def stop_all(self):
        """Stop all receivers"""
        with self.receiver_lock:
            for receiver in self.receivers.values():
                receiver.stop()
            self.receivers.clear()
