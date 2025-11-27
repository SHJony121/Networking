"""
TCP Control - Client-side TCP control channel handler
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import socket
import threading
import queue
import time
from common.protocol import *

class TCPControl:
    """Manages TCP control connection to server"""
    
    def __init__(self, server_host, server_port):
        self.server_host = server_host
        self.server_port = server_port
        self.socket = None
        self.running = False
        
        # Message handlers
        self.message_handlers = {}
        self.message_queue = queue.Queue()
        
        # Thread for receiving messages
        self.receive_thread = None
        
        # Lock for thread-safe sending
        self.send_lock = threading.Lock()
    
    def connect(self):
        """Connect to the server"""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        try:
            # Set timeout for connection only
            self.socket.settimeout(10)
            self.socket.connect((self.server_host, self.server_port))
            
            # Remove timeout for long-lived connection
            self.socket.settimeout(None)
            
            # Enable TCP keepalive to detect broken connections
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            
            print(f"[TCPControl] Connected to server {self.server_host}:{self.server_port}")
            
            # Start receive thread
            self.running = True
            self.receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
            self.receive_thread.start()
            
            return True
        
        except Exception as e:
            print(f"[TCPControl] Failed to connect: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from server"""
        self.running = False
        
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        
        print("[TCPControl] Disconnected from server")
    
    def send_message(self, msg_type, **kwargs):
        """Send a message to the server"""
        if not self.socket:
            raise Exception("Not connected to server")
        
        with self.send_lock:  # Thread-safe sending
            message = pack_tcp_message(msg_type, **kwargs)
            if msg_type == MSG_REGISTER_UDP:
                print(f"[TCPControl] Sending REGISTER_UDP message: {kwargs}")
                print(f"[TCPControl] Message packed into {len(message)} bytes")
            
            try:
                self.socket.sendall(message)  # Use sendall to ensure all bytes are sent
                if msg_type == MSG_REGISTER_UDP:
                    print(f"[TCPControl] REGISTER_UDP: All {len(message)} bytes sent successfully")
            except Exception as e:
                print(f"[TCPControl] ERROR sending {msg_type}: {e}")
                import traceback
                traceback.print_exc()
                raise
    
    def register_handler(self, msg_type, handler):
        """
        Register a handler for a specific message type
        handler(msg_dict)
        """
        self.message_handlers[msg_type] = handler
    
    def _receive_loop(self):
        """Receive messages from server in background thread"""
        print("[TCPControl] Receive loop started")
        while self.running:
            try:
                msg = unpack_tcp_message(self.socket)
                if msg is None:
                    print("[TCPControl] Connection closed by server (msg is None)")
                    break
                
                print(f"[TCPControl] Received message: {msg.get('type')}")
                # Handle message
                self._handle_message(msg)
            
            except socket.timeout:
                print("[TCPControl] Socket timeout, continuing...")
                continue
            except (ConnectionResetError, ConnectionAbortedError) as e:
                # Handle connection errors gracefully
                if self.running:
                    print(f"[TCPControl] Connection reset/aborted: {e}")
                break
            except OSError as e:
                # Handle other OS errors
                if self.running:
                    print(f"[TCPControl] OS error: {e}")
                break
            except Exception as e:
                if self.running:
                    print(f"[TCPControl] Unexpected error: {e}")
                    import traceback
                    traceback.print_exc()
                break
        
        print("[TCPControl] Receive loop ended")
        self.running = False
    
    def _handle_message(self, msg):
        """Handle incoming message"""
        msg_type = msg.get('type')
        
        # Always put in queue first for wait_for_message
        self.message_queue.put(msg)
        
        # Then call registered handler if exists
        if msg_type in self.message_handlers:
            try:
                self.message_handlers[msg_type](msg)
            except Exception as e:
                print(f"[TCPControl] Error in handler for {msg_type}: {e}")
    
    def wait_for_message(self, msg_type, timeout=10):
        """
        Wait for a specific message type
        Returns: message dict or None if timeout
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                msg = self.message_queue.get(timeout=0.1)
                if msg.get('type') == msg_type:
                    return msg
                else:
                    # Put back if not the right type
                    self.message_queue.put(msg)
            except queue.Empty:
                continue
        
        return None
    
    def is_connected(self):
        """Check if connected to server"""
        return self.socket is not None and self.running

# Convenience functions for common operations
class ClientSession:
    """High-level client session manager"""
    
    def __init__(self, server_host, server_port):
        self.tcp_control = TCPControl(server_host, server_port)
        self.meeting_code = None
        self.is_host = False
        self.client_name = None
        self.participants = []
    
    def connect(self):
        """Connect to server"""
        return self.tcp_control.connect()
    
    def disconnect(self):
        """Disconnect from server"""
        self.tcp_control.send_message(MSG_LEAVE)
        self.tcp_control.disconnect()
    
    def create_meeting(self, name):
        """Create a new meeting"""
        self.client_name = name
        self.tcp_control.send_message(MSG_CREATE_MEETING, name=name)
        
        response = self.tcp_control.wait_for_message(MSG_MEETING_CREATED)
        if response:
            self.meeting_code = response.get('meeting_code')
            self.is_host = True
            print(f"[ClientSession] Meeting created: {self.meeting_code}")
            return self.meeting_code
        
        return None
    
    def join_meeting(self, meeting_code, name):
        """Request to join a meeting"""
        self.client_name = name
        self.meeting_code = meeting_code
        
        print(f"[ClientSession] Sending join request for meeting {meeting_code}")
        self.tcp_control.send_message(MSG_REQUEST_JOIN, meeting_code=meeting_code, name=name)
        
        # Wait for either PENDING or REJECTED
        print(f"[ClientSession] Waiting for JOIN_PENDING response...")
        response = self.tcp_control.wait_for_message(MSG_JOIN_PENDING, timeout=5)
        
        if not response:
            print(f"[ClientSession] No JOIN_PENDING response received (timeout)")
            return False
        
        print(f"[ClientSession] Join request pending approval")
        
        # Now wait for ACCEPTED or REJECTED
        print(f"[ClientSession] Waiting for JOIN_ACCEPTED response...")
        response = self.tcp_control.wait_for_message(MSG_JOIN_ACCEPTED, timeout=30)
        
        if response and response.get('type') == MSG_JOIN_ACCEPTED:
            print(f"[ClientSession] Joined meeting {meeting_code}")
            return True
        elif response:
            print(f"[ClientSession] Received unexpected response: {response.get('type')}")
        else:
            print(f"[ClientSession] No JOIN_ACCEPTED response received (timeout)")
        
        print(f"[ClientSession] Failed to join meeting")
        return False
    
    def allow_participant(self, participant_name):
        """Allow a waiting participant to join (host only)"""
        if not self.is_host:
            return False
        
        self.tcp_control.send_message(MSG_ALLOW_JOIN, client_name=participant_name)
        return True
    
    def deny_participant(self, participant_name):
        """Deny a waiting participant (host only)"""
        if not self.is_host:
            return False
        
        self.tcp_control.send_message(MSG_DENY_JOIN, client_name=participant_name)
        return True
    
    def send_chat(self, message):
        """Send a chat message"""
        self.tcp_control.send_message(MSG_CHAT, message=message)
    
    def register_udp_ports(self, video_port, audio_port):
        """Register UDP receiving ports with server"""
        import time
        print(f"[ClientSession] Sending MSG_REGISTER_UDP with video_port={video_port}, audio_port={audio_port}")
        self.tcp_control.send_message(MSG_REGISTER_UDP, 
                                      video_port=video_port,
                                      audio_port=audio_port)
        # Small delay to ensure message is processed
        time.sleep(0.1)
        print(f"[ClientSession] UDP registration message sent")
    
    def leave_meeting(self):
        """Leave the current meeting"""
        self.tcp_control.send_message(MSG_LEAVE)
        self.meeting_code = None
        self.is_host = False
