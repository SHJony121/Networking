"""
Stats Collector - Collects network stats and implements adaptive streaming logic
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import threading
from collections import deque
from common.protocol import *

class StatsCollector:
    """Collects and manages network statistics"""
    
    def __init__(self, video_sender, video_receiver, audio_sender, audio_receiver, tcp_control):
        self.video_sender = video_sender
        self.video_receiver = video_receiver
        self.audio_sender = audio_sender
        self.audio_receiver = audio_receiver
        self.tcp_control = tcp_control
        
        # Stats history
        self.rtt_history = deque(maxlen=60)  # Last 60 seconds
        self.packet_loss_history = deque(maxlen=60)
        self.jitter_history = deque(maxlen=60)
        self.fps_history = deque(maxlen=60)
        self.bitrate_history = deque(maxlen=60)
        
        # Current stats
        self.current_rtt = 0
        self.current_packet_loss = 0
        self.current_jitter = 0
        self.current_fps_sent = 0
        self.current_fps_received = 0
        self.current_bitrate = 0
        
        # Thread control
        self.running = False
        self.collection_thread = None
        self.stats_lock = threading.Lock()
        
        # Last byte counts for bitrate calculation
        self.last_bytes_sent = 0
        self.last_bytes_received = 0
        self.last_bitrate_time = time.time()
    
    def start(self):
        """Start collecting stats"""
        self.running = True
        self.collection_thread = threading.Thread(target=self._collection_loop, daemon=True)
        self.collection_thread.start()
        print("[StatsCollector] Started")
    
    def stop(self):
        """Stop collecting stats"""
        self.running = False
        if self.collection_thread:
            self.collection_thread.join(timeout=2)
        print("[StatsCollector] Stopped")
    
    def _collection_loop(self):
        """Main stats collection loop"""
        while self.running:
            try:
                self._collect_stats()
                self._apply_adaptive_logic()
                self._send_stats_to_server()
                time.sleep(STATS_UPDATE_INTERVAL)
            
            except Exception as e:
                print(f"[StatsCollector] Error in collection loop: {e}")
    
    def _collect_stats(self):
        """Collect current statistics"""
        with self.stats_lock:
            # Get video receiver stats
            if self.video_receiver:
                video_stats = self.video_receiver.get_stats()
                self.current_packet_loss = video_stats.get('packet_loss_percent', 0)
                self.current_jitter = video_stats.get('jitter_ms', 0)
                self.current_fps_received = video_stats.get('fps_received', 0)
            
            # Get video sender stats
            if self.video_sender:
                sender_stats = self.video_sender.get_stats()
                self.current_fps_sent = sender_stats.get('fps', 0)
            
            # Calculate bitrate
            self._calculate_bitrate()
            
            # Estimate RTT (simplified - using jitter as proxy)
            # In production, you'd ping-pong timestamps
            self.current_rtt = self.current_jitter * 2  # Rough estimate
            
            # Add to history
            self.rtt_history.append(self.current_rtt)
            self.packet_loss_history.append(self.current_packet_loss)
            self.jitter_history.append(self.current_jitter)
            self.fps_history.append(self.current_fps_received)
            self.bitrate_history.append(self.current_bitrate)
    
    def _calculate_bitrate(self):
        """Calculate current bitrate in kbps"""
        if self.video_sender:
            sender_stats = self.video_sender.get_stats()
            current_bytes = sender_stats.get('bytes_sent', 0)
            
            current_time = time.time()
            time_diff = current_time - self.last_bitrate_time
            
            if time_diff > 0:
                bytes_diff = current_bytes - self.last_bytes_sent
                bitrate_bps = (bytes_diff * 8) / time_diff
                self.current_bitrate = bitrate_bps / 1000  # Convert to kbps
                
                self.last_bytes_sent = current_bytes
                self.last_bitrate_time = current_time
    
    def _apply_adaptive_logic(self):
        """Apply adaptive streaming logic based on network conditions"""
        if not self.video_sender:
            return
        
        # Adjust video quality based on packet loss and RTT
        self.video_sender.adjust_quality(
            packet_loss=self.current_packet_loss,
            rtt=self.current_rtt
        )
    
    def _send_stats_to_server(self):
        """Send stats to server (for coordination between peers)"""
        if self.tcp_control and self.tcp_control.is_connected():
            try:
                self.tcp_control.send_message(
                    MSG_VIDEO_STATS,
                    loss=round(self.current_packet_loss, 2),
                    rtt=round(self.current_rtt, 2),
                    fps_recv=round(self.current_fps_received, 2),
                    bitrate=round(self.current_bitrate, 2)
                )
            except:
                pass  # Don't crash if sending fails
    
    def get_current_stats(self):
        """Get current statistics (thread-safe)"""
        with self.stats_lock:
            return {
                'rtt_ms': round(self.current_rtt, 2),
                'packet_loss_percent': round(self.current_packet_loss, 2),
                'jitter_ms': round(self.current_jitter, 2),
                'fps_sent': round(self.current_fps_sent, 2),
                'fps_received': round(self.current_fps_received, 2),
                'bitrate_kbps': round(self.current_bitrate, 2)
            }
    
    def get_stats_history(self):
        """Get statistics history for graphing"""
        with self.stats_lock:
            return {
                'rtt': list(self.rtt_history),
                'packet_loss': list(self.packet_loss_history),
                'jitter': list(self.jitter_history),
                'fps': list(self.fps_history),
                'bitrate': list(self.bitrate_history)
            }
    
    def get_quality_recommendation(self):
        """Get quality recommendation based on network conditions"""
        with self.stats_lock:
            if self.current_packet_loss > 15 or self.current_rtt > 400:
                return "Poor - Consider lowering quality"
            elif self.current_packet_loss > 5 or self.current_rtt > 200:
                return "Fair - Current quality appropriate"
            else:
                return "Good - Can increase quality"
    
    def calculate_average_rtt(self, window=10):
        """Calculate average RTT over last N samples"""
        with self.stats_lock:
            if len(self.rtt_history) == 0:
                return 0
            recent = list(self.rtt_history)[-window:]
            return sum(recent) / len(recent)
    
    def calculate_average_packet_loss(self, window=10):
        """Calculate average packet loss over last N samples"""
        with self.stats_lock:
            if len(self.packet_loss_history) == 0:
                return 0
            recent = list(self.packet_loss_history)[-window:]
            return sum(recent) / len(recent)
