"""
Congestion Control - TCP Reno implementation for file transfers
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import threading
import time
from common.protocol import *

class FileManager:
    """Manages file transfer sessions with congestion control"""
    
    def __init__(self):
        self.lock = threading.Lock()
        
        # Active file transfers
        # {transfer_id: FileTransferSession}
        self.transfers = {}
    
    def create_transfer(self, sender_socket, filename, filesize):
        """Create a new file transfer session"""
        transfer_id = f"{id(sender_socket)}_{filename}_{int(time.time() * 1000)}"
        
        with self.lock:
            self.transfers[transfer_id] = FileTransferSession(
                transfer_id, sender_socket, filename, filesize
            )
        
        return transfer_id
    
    def get_transfer(self, transfer_id):
        """Get a file transfer session"""
        with self.lock:
            return self.transfers.get(transfer_id)
    
    def remove_transfer(self, transfer_id):
        """Remove a file transfer session"""
        with self.lock:
            if transfer_id in self.transfers:
                del self.transfers[transfer_id]

class FileTransferSession:
    """Represents a single file transfer with congestion control"""
    
    def __init__(self, transfer_id, sender_socket, filename, filesize):
        self.transfer_id = transfer_id
        self.sender_socket = sender_socket
        self.filename = filename
        self.filesize = filesize
        
        # TCP Reno congestion control variables
        self.cwnd = INITIAL_CWND
        self.ssthresh = INITIAL_SSTHRESH
        
        # Transfer state
        self.bytes_sent = 0
        self.chunks_sent = 0
        self.chunks_acked = 0
        
        # Timing for timeout detection
        self.last_ack_time = time.time()
        self.rtt_samples = []
        self.estimated_rtt = 0.1  # 100ms initial estimate
        
        self.lock = threading.Lock()
    
    def get_chunk_size(self):
        """Calculate current chunk size based on cwnd"""
        with self.lock:
            chunk_size = int(self.cwnd * BASE_CHUNK_SIZE)
            return min(chunk_size, BASE_CHUNK_SIZE * MAX_CWND)
    
    def on_ack_received(self, chunk_id, rtt=None):
        """Handle ACK reception - update cwnd according to TCP Reno"""
        with self.lock:
            self.chunks_acked += 1
            self.last_ack_time = time.time()
            
            # Update RTT estimate if provided
            if rtt is not None:
                self.rtt_samples.append(rtt)
                if len(self.rtt_samples) > 10:
                    self.rtt_samples.pop(0)
                self.estimated_rtt = sum(self.rtt_samples) / len(self.rtt_samples)
            
            # TCP Reno congestion control algorithm
            if self.cwnd < self.ssthresh:
                # Slow start: exponential growth
                self.cwnd = min(self.cwnd * 2, MAX_CWND)
            else:
                # Congestion avoidance: linear growth
                self.cwnd = min(self.cwnd + 1, MAX_CWND)
    
    def on_timeout(self):
        """Handle timeout - reduce cwnd according to TCP Reno"""
        with self.lock:
            # Multiplicative decrease
            self.ssthresh = max(self.cwnd // 2, 1)
            self.cwnd = INITIAL_CWND
            
            print(f"[FileTransfer] Timeout detected for {self.filename}, "
                  f"cwnd reset to {self.cwnd}, ssthresh set to {self.ssthresh}")
    
    def check_timeout(self, timeout_threshold=5.0):
        """Check if a timeout has occurred"""
        with self.lock:
            time_since_ack = time.time() - self.last_ack_time
            return time_since_ack > timeout_threshold
    
    def get_cwnd(self):
        """Get current congestion window size"""
        with self.lock:
            return self.cwnd
    
    def get_progress(self):
        """Get transfer progress"""
        with self.lock:
            return {
                'bytes_sent': self.bytes_sent,
                'filesize': self.filesize,
                'chunks_sent': self.chunks_sent,
                'chunks_acked': self.chunks_acked,
                'cwnd': self.cwnd,
                'ssthresh': self.ssthresh,
                'estimated_rtt': self.estimated_rtt
            }
