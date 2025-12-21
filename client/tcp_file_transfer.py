"""
TCP File Transfer - Client-side file transfer with congestion control
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import hashlib
import base64
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
            
            # Read and send file in chunks
            with open(filepath, 'rb') as f:
                chunk_id = 0
                
                while True:
                    # Read chunk based on current cwnd
                    chunk_size = self.get_chunk_size()
                    chunk_data = f.read(chunk_size)
                    
                    if not chunk_data:
                        break
                    
                    # Send chunk
                    self.send_chunk(chunk_id, chunk_data)
                    chunk_id += 1
                    
                    # Update progress
                    if progress_callback:
                        progress_callback(self.bytes_sent, self.filesize, self.cwnd)
                    
                    # Simple flow control: wait a bit to avoid overwhelming
                    time.sleep(0.01)
            
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
            self.in_progress = False
    
    def send_chunk(self, chunk_id, data):
        """Send a file chunk"""
        # Encode data as base64 for JSON transmission
        data_b64 = base64.b64encode(data).decode('utf-8')
        
        # Record send time
        self.chunk_send_times[chunk_id] = time.time()
        
        # Send chunk
        self.tcp_control.send_message(
            MSG_FILE_CHUNK,
            chunk_id=chunk_id,
            data=data_b64,
            target_name=self.target
        )
        
        self.chunks_sent += 1
        self.bytes_sent += len(data)
    
    def on_ack_received(self, chunk_id, server_cwnd=None):
        """Handle ACK from receiver"""
        self.chunks_acked += 1
        self.last_ack_time = time.time()
        
        # Calculate RTT
        if chunk_id in self.chunk_send_times:
            rtt = time.time() - self.chunk_send_times[chunk_id]
            self.rtt_history.append(rtt * 1000)  # Convert to ms
            del self.chunk_send_times[chunk_id]
        
        # Update cwnd according to TCP Reno
        if self.cwnd < self.ssthresh:
            # Slow start
            self.cwnd = min(self.cwnd * 2, MAX_CWND)
        else:
            # Congestion avoidance
            self.cwnd = min(self.cwnd + 1, MAX_CWND)
        
        self.cwnd_history.append(self.cwnd)
    
    def on_timeout(self):
        """Handle timeout"""
        self.ssthresh = max(self.cwnd // 2, 1)
        self.cwnd = INITIAL_CWND
        self.cwnd_history.append(self.cwnd)
        
        print(f"[FileTransfer] Timeout! cwnd reset to {self.cwnd}, ssthresh={self.ssthresh}")
    
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
            'rtt_history': self.rtt_history
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
        data = base64.b64decode(data_b64)
        self.file_handle.write(data)
        self.bytes_received += len(data)
        
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
