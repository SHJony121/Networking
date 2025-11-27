"""
Audio Receiver - Receives and plays audio via UDP
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pyaudio
import time
import socket
import threading
from queue import Queue
from common.protocol import *

class AudioReceiver:
    """Receives and plays audio via UDP"""
    
    def __init__(self, local_udp_port):
        self.local_udp_port = local_udp_port
        
        # Audio settings
        self.sample_rate = AUDIO_SAMPLE_RATE
        self.channels = AUDIO_CHANNELS
        self.chunk_size = AUDIO_CHUNK_SIZE
        
        # PyAudio
        self.audio = None
        self.stream = None
        
        # UDP socket
        self.socket = None
        self.running = False
        
        # Audio buffer (queue)
        self.audio_queue = Queue(maxsize=50)
        
        # Stats
        self.packets_received = 0
        self.bytes_received = 0
        self.packets_lost = 0
        self.last_audio_id = -1
        
        # Threads
        self.receive_thread = None
        self.play_thread = None
    
    def start(self):
        """Start receiving and playing audio"""
        try:
            # Initialize PyAudio
            self.audio = pyaudio.PyAudio()
            self.stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=self.sample_rate,
                output=True,
                frames_per_buffer=self.chunk_size
            )
            
            # Initialize UDP socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.bind(('0.0.0.0', self.local_udp_port))
            
            # Get the actual port if 0 was specified (OS-assigned)
            if self.local_udp_port == 0:
                self.local_udp_port = self.socket.getsockname()[1]
            
            self.running = True
            
            # Start receive thread
            self.receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
            self.receive_thread.start()
            
            # Start playback thread
            self.play_thread = threading.Thread(target=self._play_loop, daemon=True)
            self.play_thread.start()
            
            print(f"[AudioReceiver] Started on port {self.local_udp_port}")
            return True
        
        except Exception as e:
            print(f"[AudioReceiver] Failed to start: {e}")
            return False
    
    def stop(self):
        """Stop receiving audio"""
        self.running = False
        
        if self.receive_thread:
            self.receive_thread.join(timeout=2)
        
        if self.play_thread:
            self.play_thread.join(timeout=2)
        
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        
        if self.audio:
            self.audio.terminate()
        
        if self.socket:
            self.socket.close()
        
        print("[AudioReceiver] Stopped")
    
    def _receive_loop(self):
        """Main receiving loop"""
        self.socket.settimeout(0.1)
        
        while self.running:
            try:
                data, addr = self.socket.recvfrom(65535)
                self._process_packet(data, addr)
            
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"[AudioReceiver] Error receiving: {e}")
    
    def _process_packet(self, data, addr):
        """Process received audio packet"""
        try:
            # Parse header
            if len(data) < AUDIO_HEADER_SIZE:
                return
            
            header = unpack_audio_header(data)
            audio_data = data[AUDIO_HEADER_SIZE:]
            
            # Check for lost packets
            if self.last_audio_id != -1:
                expected_id = (self.last_audio_id + 1) % (2**32)
                if header['audio_id'] != expected_id:
                    lost = (header['audio_id'] - expected_id) % (2**32)
                    self.packets_lost += lost
            
            self.last_audio_id = header['audio_id']
            
            # Add to playback queue
            if not self.audio_queue.full():
                self.audio_queue.put(audio_data)
            
            # Update stats
            self.packets_received += 1
            self.bytes_received += len(data)
        
        except Exception as e:
            print(f"[AudioReceiver] Error processing packet: {e}")
    
    def _play_loop(self):
        """Playback loop"""
        while self.running:
            try:
                # Get audio from queue
                if not self.audio_queue.empty():
                    audio_data = self.audio_queue.get(timeout=0.1)
                    
                    # Play audio
                    if self.stream.is_active():
                        self.stream.write(audio_data)
                else:
                    # Play silence if no data
                    silence = b'\x00' * (self.chunk_size * 2)  # 16-bit = 2 bytes per sample
                    self.stream.write(silence)
                    time.sleep(0.01)
            
            except Exception as e:
                if self.running:
                    print(f"[AudioReceiver] Error in play loop: {e}")
    
    def get_stats(self):
        """Get receiver statistics"""
        total_expected = self.packets_received + self.packets_lost
        packet_loss_pct = (self.packets_lost / total_expected * 100) if total_expected > 0 else 0
        
        return {
            'packets_received': self.packets_received,
            'bytes_received': self.bytes_received,
            'packets_lost': self.packets_lost,
            'packet_loss_percent': packet_loss_pct,
            'queue_size': self.audio_queue.qsize()
        }

class MultiAudioReceiver:
    """Manages multiple audio streams and mixes them"""
    
    def __init__(self, base_udp_port):
        self.base_udp_port = base_udp_port
        self.receivers = {}  # {participant_id: AudioReceiver}
        self.receiver_lock = threading.Lock()
    
    def add_participant(self, participant_id):
        """Add a new participant audio stream"""
        with self.receiver_lock:
            if participant_id not in self.receivers:
                # Note: In production, you'd need audio mixing
                # For now, each participant uses separate port (simplified)
                port = self.base_udp_port + len(self.receivers) + 100
                receiver = AudioReceiver(port)
                receiver.start()
                self.receivers[participant_id] = receiver
                print(f"[MultiAudioReceiver] Added participant {participant_id} on port {port}")
    
    def remove_participant(self, participant_id):
        """Remove a participant audio stream"""
        with self.receiver_lock:
            if participant_id in self.receivers:
                self.receivers[participant_id].stop()
                del self.receivers[participant_id]
                print(f"[MultiAudioReceiver] Removed participant {participant_id}")
    
    def stop_all(self):
        """Stop all receivers"""
        with self.receiver_lock:
            for receiver in self.receivers.values():
                receiver.stop()
            self.receivers.clear()
