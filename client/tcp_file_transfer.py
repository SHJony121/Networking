import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import hashlib
import base64
import threading
from common.protocol import *

class TCPFileTransfer:
    """Handles file transfer with TCP Reno congestion control"""
    
    def __init__(self, tcp_control):
        self.tcp_control = tcp_control
        
        # Congestion control state
        self.cwnd = INITIAL_CWND
        self.ssthresh = INITIAL_SSTHRESH
        
        # Transfer state
        self.in_progress = False
        self.filename = None
        self.filesize = 0
        self.bytes_sent = 0
        self.chunks_sent = 0
        self.chunks_acked = 0
        
        # Timing
        self.chunk_send_times = {}  # {chunk_id: send_time}
        self.last_ack_time = time.time()
        self.estimated_rtt = None
        self.dev_rtt = None
        self.timeout_interval = 2.0 # Default timeout
        
        # Reno State
        self.packet_buffer = {}     # {chunk_id: data} - For retransmission
        self.unacked_chunks = set() # {chunk_id}
        self.dup_acks = 0           # Count of duplicate ACKs
        self.last_acked_chunk = -1  # Last cumulative ACK
        self.fast_recovery = False  # Are we in fast recovery?
        
        # Lock for thread safety (since ACKs come from another thread)
        self.lock = threading.RLock()
        
        # Stats for UI
        self.cwnd_history = []
        self.rtt_history = []
    
    def send_file(self, filepath, target="Everyone", progress_callback=None):
        """
        Send a file with congestion control
        progress_callback(bytes_sent, total_bytes, cwnd)
        """
        if self.in_progress:
            raise Exception("File transfer already in progress")
        
        self.in_progress = True
        self.filename = os.path.basename(filepath)
        self.filesize = os.path.getsize(filepath)
        self.target = target  # Store target
        print(f"[TCPFileTransfer] send_file: starting {self.filename} ({self.filesize} bytes)")
        self.bytes_sent = 0
        self.chunks_sent = 0
        self.chunks_acked = 0
        
        # Reset congestion control
        self.cwnd = INITIAL_CWND
        self.ssthresh = INITIAL_SSTHRESH
        self.cwnd_history = [self.cwnd]
        
        try:
            # Send FILE_START
            chunk_size = self.get_chunk_size()
            self.tcp_control.send_message(
                MSG_FILE_START,
                filename=self.filename,
                filesize=self.filesize,
                chunk_size=chunk_size,
                target_name=self.target
            )
            
            # Read all file data first (simplification for reliability)
            # For very large files, this should be buffered reading, but for now this ensures we have data for retransmits
            with open(filepath, 'rb') as f:
                file_data = f.read()
            
            total_chunks = (len(file_data) + BASE_CHUNK_SIZE - 1) // BASE_CHUNK_SIZE
            print(f"[FileTransfer] Total chunks to send: {total_chunks}")
            
            current_chunk_id = 0
            
            while self.chunks_acked < total_chunks:
                # print(f"[FileTransfer] Loop: acked={self.chunks_acked}/{total_chunks} cwnd={self.cwnd} unacked={len(self.unacked_chunks)}")
                # 1. Check for timeouts
                with self.lock:
                    if time.time() - self.last_ack_time > self.timeout_interval: # Dynamic timeout
                        print(f"[FileTransfer] TIMEOUT! Resetting cwnd.")
                        self.on_timeout()
                        self.last_ack_time = time.time()
                        # Go back to last acked + 1
                        current_chunk_id = self.last_acked_chunk + 1
                        # Retransmit immediately
                        if current_chunk_id < total_chunks:
                            self._send_chunk_internal(current_chunk_id, file_data)
                
                # 2. Send new chunks if window allows
                with self.lock:
                    in_flight = len(self.unacked_chunks)
                    can_send = in_flight < self.cwnd
                
                if can_send and current_chunk_id < total_chunks:
                    # Send next chunk
                    self._send_chunk_internal(current_chunk_id, file_data)
                    current_chunk_id += 1
                else:
                    # Window full or out of data, wait for ACKs
                    time.sleep(0.01) # Short sleep to prevent CPU burn
            
                # Update progress
                if progress_callback:
                    progress_callback(self.bytes_sent, self.filesize, self.cwnd)
            
            # Calculate checksum
            checksum = self.calculate_file_checksum(filepath)
            
            # Send FILE_END
            self.tcp_control.send_message(
                MSG_FILE_END,
                checksum=checksum,
                target_name=self.target
            )
            
            print(f"[FileTransfer] File '{self.filename}' sent successfully")
            return True
        
        except Exception as e:
            print(f"[FileTransfer] Error sending file: {e}")
            return False
        
        finally:
            print("[FileTransfer] Cleaning up transfer state")
            self.in_progress = False
    
    def _send_chunk_internal(self, chunk_id, all_data):
        """Helper to send a specific chunk"""
        start_idx = chunk_id * BASE_CHUNK_SIZE
        end_idx = min(start_idx + BASE_CHUNK_SIZE, len(all_data))
        chunk_data = all_data[start_idx:end_idx]
        
        self.send_chunk(chunk_id, chunk_data)

    def send_chunk(self, chunk_id, data):
        """Send a file chunk"""
        try:
            # Encode data as base64 for JSON transmission
            data_b64 = base64.b64encode(data).decode('utf-8')
        except Exception as e:
            print(f"[FileTransfer] ERROR encoding chunk {chunk_id}: {e}")
            return

        with self.lock:
            # Record send time and state
            self.chunk_send_times[chunk_id] = time.time()
            self.unacked_chunks.add(chunk_id)
            # Note: We rely on all_data logic in main loop for retransmits to save memory here
            # or we could buffer just the active window.
            # For simplicity, main loop holds all_data.
        
        # Send chunk
        try:
            self.tcp_control.send_message(
                MSG_FILE_CHUNK,
                chunk_id=chunk_id,
                data=data_b64,
                target_name=self.target
            )
            print(f"[FileTransfer] SEND CHUNK {chunk_id} (cwnd={self.cwnd})")
            if chunk_id > self.last_acked_chunk: # Only count new progress
                self.bytes_sent = max(self.bytes_sent, (chunk_id + 1) * BASE_CHUNK_SIZE) # Approx
                self.chunks_sent = max(self.chunks_sent, chunk_id + 1)
        except Exception as e:
            print(f"[FileTransfer] failed to send chunk {chunk_id}: {e}")
    
    def on_ack_received(self, chunk_id, server_cwnd=None):
        """Handle ACK from receiver (Reno Implementation)"""
        print(f"[FileTransfer] GOT ACK {chunk_id}")
        with self.lock:
            self.last_ack_time = time.time()
            
            # DUPLICATE ACK detection
            if chunk_id <= self.last_acked_chunk:
                pass
            
            if chunk_id in self.unacked_chunks:
                self.unacked_chunks.remove(chunk_id)
                self.chunks_acked += 1
                self.last_acked_chunk = max(self.last_acked_chunk, chunk_id)
                
                # --- RTT Calculation (Jacobson's Algorithm) ---
                if chunk_id in self.chunk_send_times:
                    sample_rtt = time.time() - self.chunk_send_times[chunk_id]
                    # Cleanup old send time
                    del self.chunk_send_times[chunk_id]
                    
                    if self.estimated_rtt is None:
                        # First measurement
                        self.estimated_rtt = sample_rtt
                        self.dev_rtt = sample_rtt / 2
                    else:
                        # Update EstRTT = (1-a)*EstRTT + a*SampleRTT
                        # alpha = 0.125
                        self.estimated_rtt = 0.875 * self.estimated_rtt + 0.125 * sample_rtt
                        
                        # Update DevRTT = (1-b)*DevRTT + b*|SampleRTT - EstRTT|
                        # beta = 0.25
                        self.dev_rtt = 0.75 * self.dev_rtt + 0.25 * abs(sample_rtt - self.estimated_rtt)
                    
                    # Update Timeout Interval = EstRTT + 4*DevRTT
                    self.timeout_interval = self.estimated_rtt + 4 * self.dev_rtt
                    # Clamp timeout to reasonable bounds (e.g. min 1s to allow processing)
                    self.timeout_interval = max(self.timeout_interval, 1.0)
                
                # New ACK - Reno Increase
                self.dup_acks = 0
                self.fast_recovery = False
                
                if self.cwnd < self.ssthresh:
                    # Slow start
                    self.cwnd = min(self.cwnd + 1, MAX_CWND) # +1 per ACK is exponential growth (doubles per RTT)
                else:
                    # Congestion avoidance: +1/cwnd per ACK (approx +1 per RTT)
                    self.cwnd = min(self.cwnd + (1.0 / self.cwnd), MAX_CWND)
            
            else:
                pass

            # Update cwnd history
            self.cwnd_history.append(self.cwnd)
            # Log current RTT for graph (optional, using EstRTT)
            if self.estimated_rtt:
                self.rtt_history.append(self.estimated_rtt * 1000)
    
    def on_timeout(self):
        """Handle timeout"""
        self.ssthresh = max(self.cwnd // 2, 1)
        self.cwnd = INITIAL_CWND
        self.cwnd_history.append(self.cwnd)
        
        # Exponential Backoff for timeout? 
        # Usually double timeout on consecutive timeouts, but reset on fresh ACK.
        # For simplicity, we just keep current estimated timeout.
        
        print(f"[FileTransfer] Timeout! cwnd reset to {self.cwnd}, ssthresh={self.ssthresh}, timeout={self.timeout_interval:.2f}s")
    
    def get_chunk_size(self):
        """Get current chunk size based on cwnd"""
        return int(self.cwnd * BASE_CHUNK_SIZE)
    
    def calculate_file_checksum(self, filepath):
        """Calculate MD5 checksum of file"""
        md5 = hashlib.md5()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b""):
                md5.update(chunk)
        return md5.hexdigest()
    
    def get_stats(self):
        """Get transfer statistics"""
        return {
            'filename': self.filename,
            'filesize': self.filesize,
            'bytes_sent': self.bytes_sent,
            'chunks_sent': self.chunks_sent,
            'chunks_acked': self.chunks_acked,
            'cwnd': self.cwnd,
            'ssthresh': self.ssthresh,
            'cwnd_history': self.cwnd_history,
            'rtt_history': self.rtt_history,
            'timeout_interval': self.timeout_interval
        }

class FileReceiver:
    """Handles receiving files"""
    
    def __init__(self, save_dir='downloads'):
        self.save_dir = save_dir
        self.receiving = False
        self.current_file = None
        self.file_handle = None
        self.expected_size = 0
        self.bytes_received = 0
        
        # Create downloads directory
        os.makedirs(save_dir, exist_ok=True)
    
    def start_receiving(self, filename, filesize):
        """Start receiving a file"""
        self.receiving = True
        self.current_file = filename
        self.expected_size = filesize
        self.bytes_received = 0
        
        filepath = os.path.join(self.save_dir, filename)
        self.file_handle = open(filepath, 'wb')
        
        print(f"[FileReceiver] Receiving file: {filename} ({filesize} bytes)")
    
    def receive_chunk(self, chunk_id, data_b64):
        """Receive a file chunk"""
        if not self.receiving or not self.file_handle:
            return
        
        # Decode base64 data
        # Decode base64 data
        data = base64.b64decode(data_b64)
        
        # Calculate offset and seek (Prevent duplicates/corruption)
        offset = chunk_id * BASE_CHUNK_SIZE
        self.file_handle.seek(offset)
        self.file_handle.write(data)
        
        # Update progress (approximate, since we might rewrite)
        # self.bytes_received += len(data) # This is buggy if we rewrite
        # Better to track how many unique chunks we have, but for now this is fine for UI bar
        self.bytes_received = min(self.bytes_received + len(data), self.expected_size)
        
        # Send ACK (handled by caller)
    
    def finish_receiving(self, checksum):
        """Finish receiving file"""
        if self.file_handle:
            self.file_handle.close()
            self.file_handle = None
        
        # Verify checksum
        filepath = os.path.join(self.save_dir, self.current_file)
        actual_checksum = self.calculate_file_checksum(filepath)
        
        if actual_checksum == checksum:
            print(f"[FileReceiver] File received successfully: {self.current_file}")
        else:
            print(f"[FileReceiver] WARNING: Checksum mismatch for {self.current_file}")
        
        self.receiving = False
    
    def calculate_file_checksum(self, filepath):
        """Calculate MD5 checksum"""
        md5 = hashlib.md5()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b""):
                md5.update(chunk)
        return md5.hexdigest()
