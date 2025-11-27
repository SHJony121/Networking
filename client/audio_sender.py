"""
Audio Sender - Captures and sends audio via UDP
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pyaudio
import time
import socket
import threading
from common.protocol import *

class AudioSender:
    """Captures audio and sends it to server via UDP"""
    
    def __init__(self, server_host, server_udp_port):
        self.server_host = server_host
        self.server_udp_port = server_udp_port
        
        # Audio settings
        self.sample_rate = AUDIO_SAMPLE_RATE
        self.channels = AUDIO_CHANNELS
        self.chunk_size = AUDIO_CHUNK_SIZE
        
        # PyAudio
        self.audio = None
        self.stream = None
        self.running = False
        self.enabled = True
        
        # UDP socket
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # Packet tracking
        self.audio_id = 0
        self.packets_sent = 0
        self.bytes_sent = 0
        
        # Thread
        self.send_thread = None
    
    def start(self):
        """Start audio capture and sending"""
        try:
            self.audio = pyaudio.PyAudio()
            
            # Open audio stream
            self.stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size
            )
            
            self.running = True
            self.send_thread = threading.Thread(target=self._send_loop, daemon=True)
            self.send_thread.start()
            
            print(f"[AudioSender] Started: {self.sample_rate}Hz, {self.channels} channel(s)")
            return True
        
        except Exception as e:
            print(f"[AudioSender] Failed to start: {e}")
            return False
    
    def stop(self):
        """Stop audio capture"""
        self.running = False
        
        if self.send_thread:
            self.send_thread.join(timeout=2)
        
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        
        if self.audio:
            self.audio.terminate()
        
        print("[AudioSender] Stopped")
    
    def set_enabled(self, enabled):
        """Enable/disable audio sending"""
        self.enabled = enabled
        print(f"[AudioSender] {'Enabled' if enabled else 'Muted'}")
    
    def _send_loop(self):
        """Main sending loop"""
        while self.running:
            try:
                if self.enabled and self.stream.is_active():
                    # Read audio chunk
                    audio_data = self.stream.read(self.chunk_size, exception_on_overflow=False)
                    
                    # Send packet
                    self._send_audio_packet(audio_data)
                else:
                    # Send silence if muted
                    time.sleep(0.02)  # 20ms sleep
            
            except Exception as e:
                if self.running:
                    print(f"[AudioSender] Error in send loop: {e}")
                time.sleep(0.1)
    
    def _send_audio_packet(self, audio_data):
        """Send an audio packet"""
        try:
            # Create packet header
            timestamp = int(time.time() * 1000000)  # microseconds
            header = pack_audio_header(
                self.audio_id,
                timestamp,
                self.sample_rate,
                self.channels,
                len(audio_data)
            )
            
            # Send packet
            packet = header + audio_data
            self.socket.sendto(packet, (self.server_host, self.server_udp_port))
            
            # Update counters
            self.audio_id = (self.audio_id + 1) % (2**32)
            self.packets_sent += 1
            self.bytes_sent += len(packet)
        
        except Exception as e:
            print(f"[AudioSender] Error sending packet: {e}")
    
    def get_stats(self):
        """Get sender statistics"""
        return {
            'packets_sent': self.packets_sent,
            'bytes_sent': self.bytes_sent,
            'sample_rate': self.sample_rate,
            'enabled': self.enabled
        }
