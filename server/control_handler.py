"""
Control Handler - Handles TCP control channel messages from clients
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.protocol import *
import threading
import socket

class ControlHandler:
    """Handles TCP control messages from clients"""
    
    def __init__(self, meeting_manager, file_manager):
        self.meeting_manager = meeting_manager
        self.file_manager = file_manager
        self.running = True
    
    def handle_client(self, client_socket, client_addr):
        """Handle a single client connection"""
        print(f"[ControlHandler] Client connected from {client_addr}")
        
        try:
            # Configure socket
            client_socket.settimeout(None)  # No timeout for long-lived connections
            client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)  # Enable keepalive
            
            while self.running:
                try:
                    msg = unpack_tcp_message(client_socket)
                    if msg is None:
                        print(f"[ControlHandler] Client {client_addr} connection closed (msg is None)")
                        break
                    
                    msg_type = msg.get('type')
                    
                    # Log ALL messages, not just some
                    if msg_type != "VIDEO_STATS":  # Don't spam with video stats
                        print(f"[ControlHandler] Received message from {client_addr}: {msg_type}")
                        print(f"[ControlHandler] Full message: {msg}")
                    else:
                        print(f"[ControlHandler] Received message from {client_addr}: {msg_type}")
                    
                    self.process_message(client_socket, msg)
                except socket.timeout:
                    continue  # Continue on timeout
                except (ConnectionResetError, ConnectionAbortedError, OSError) as e:
                    print(f"[ControlHandler] Connection error with client {client_addr}: {e}")
                    break
        
        except Exception as e:
            print(f"[ControlHandler] Error handling client {client_addr}: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            # Clean up when client disconnects
            self.meeting_manager.leave_meeting(client_socket)
            try:
                client_socket.close()
            except:
                pass
            print(f"[ControlHandler] Client {client_addr} disconnected")
    
    def process_message(self, client_socket, msg):
        """Process incoming message from client"""
        msg_type = msg.get('type')
        
        if msg_type == MSG_CREATE_MEETING:
            self.handle_create_meeting(client_socket, msg)
        
        elif msg_type == MSG_REQUEST_JOIN:
            self.handle_request_join(client_socket, msg)
        
        elif msg_type == MSG_ALLOW_JOIN:
            self.handle_allow_join(client_socket, msg)
        
        elif msg_type == MSG_DENY_JOIN:
            self.handle_deny_join(client_socket, msg)
        
        elif msg_type == MSG_CHAT:
            self.handle_chat(client_socket, msg)
        
        elif msg_type == MSG_FILE_START:
            self.handle_file_start(client_socket, msg)
        
        elif msg_type == MSG_FILE_CHUNK:
            self.handle_file_chunk(client_socket, msg)
        
        elif msg_type == MSG_FILE_ACK:
            self.handle_file_ack(client_socket, msg)
        
        elif msg_type == MSG_FILE_END:
            self.handle_file_end(client_socket, msg)
        
        elif msg_type == MSG_VIDEO_STATS:
            self.handle_video_stats(client_socket, msg)
        
        elif msg_type == MSG_LEAVE:
            self.handle_leave(client_socket, msg)
        
        elif msg_type == MSG_HEARTBEAT:
            self.handle_heartbeat(client_socket, msg)
        
        elif msg_type == MSG_REGISTER_UDP:
            self.handle_register_udp(client_socket, msg)
        
        else:
            print(f"[ControlHandler] Unknown message type: {msg_type}")
    
    def handle_create_meeting(self, client_socket, msg):
        """Handle CREATE_MEETING request"""
        host_name = msg.get('name', 'Unknown')
        meeting_code = self.meeting_manager.create_meeting(client_socket, host_name)
        
        response = pack_tcp_message(MSG_MEETING_CREATED, meeting_code=meeting_code)
        client_socket.sendall(response)
    
    def handle_request_join(self, client_socket, msg):
        """Handle REQUEST_JOIN request"""
        meeting_code = msg.get('meeting_code')
        client_name = msg.get('name', 'Unknown')
        
        success, message = self.meeting_manager.request_join(client_socket, meeting_code, client_name)
        
        if success:
            # Notify host of new join request
            host_socket = self.meeting_manager.get_host_socket(meeting_code)
            if host_socket:
                notify_msg = pack_tcp_message(
                    MSG_NEW_JOIN_REQUEST,
                    client_name=client_name,
                    client_socket_id=id(client_socket)
                )
                try:
                    host_socket.sendall(notify_msg)
                except:
                    pass
            
            # Send pending response to requester
            response = pack_tcp_message(MSG_JOIN_PENDING, message=message)
            client_socket.sendall(response)
        else:
            response = pack_tcp_message(MSG_JOIN_REJECTED, reason=message)
            client_socket.sendall(response)
    
    def handle_allow_join(self, client_socket, msg):
        """Handle ALLOW_JOIN request from host"""
        # Find the waiting client socket by ID (simplified, in production use better identifier)
        waiting_clients = self.meeting_manager.get_waiting_list(
            self.meeting_manager.get_client_info(client_socket)['meeting']
        )
        
        allowed_client_name = msg.get('client_name')
        allowed_socket = None
        
        for waiting_client in waiting_clients:
            if waiting_client['name'] == allowed_client_name:
                allowed_socket = waiting_client['socket']
                break
        
        if allowed_socket:
            success = self.meeting_manager.allow_join(allowed_socket)
            if success:
                # Notify the allowed client
                response = pack_tcp_message(MSG_JOIN_ACCEPTED)
                try:
                    allowed_socket.sendall(response)
                except:
                    pass
                
                # Broadcast to all participants that someone joined
                client_info = self.meeting_manager.get_client_info(allowed_socket)
                meeting_code = client_info['meeting']
                self.broadcast_to_meeting(
                    meeting_code,
                    MSG_PARTICIPANT_JOINED,
                    participant_name=client_info['name']
                )
    
    def handle_deny_join(self, client_socket, msg):
        """Handle DENY_JOIN request from host"""
        denied_client_name = msg.get('client_name')
        meeting_code = self.meeting_manager.get_client_info(client_socket)['meeting']
        waiting_clients = self.meeting_manager.get_waiting_list(meeting_code)
        
        denied_socket = None
        for waiting_client in waiting_clients:
            if waiting_client['name'] == denied_client_name:
                denied_socket = waiting_client['socket']
                break
        
        if denied_socket:
            self.meeting_manager.deny_join(denied_socket)
            response = pack_tcp_message(MSG_JOIN_REJECTED, reason="Host denied your request")
            try:
                denied_socket.sendall(response)
            except:
                pass
    
    def handle_chat(self, client_socket, msg):
        """Handle CHAT message"""
        client_info = self.meeting_manager.get_client_info(client_socket)
        if not client_info:
            return
        
        meeting_code = client_info['meeting']
        message_text = msg.get('message')
        sender_name = client_info['name']
        
        # Broadcast to all participants in the meeting
        self.broadcast_to_meeting(
            meeting_code,
            MSG_CHAT_BROADCAST,
            sender_name=sender_name,
            message=message_text
        )
    
    def handle_file_start(self, client_socket, msg):
        """Handle FILE_START message"""
        client_info = self.meeting_manager.get_client_info(client_socket)
        if not client_info:
            return
        
        meeting_code = client_info['meeting']
        filename = msg.get('filename')
        filesize = msg.get('filesize')
        
        # Notify all participants
        self.broadcast_to_meeting(
            meeting_code,
            MSG_FILE_START_NOTIFY,
            sender_name=client_info['name'],
            filename=filename,
            filesize=filesize,
            exclude_socket=client_socket
        )
    
    def handle_file_chunk(self, client_socket, msg):
        """Handle FILE_CHUNK message and forward to participants"""
        client_info = self.meeting_manager.get_client_info(client_socket)
        if not client_info:
            return
        
        meeting_code = client_info['meeting']
        
        # Forward chunk to all participants except sender
        self.broadcast_to_meeting(
            meeting_code,
            MSG_FILE_CHUNK_FORWARD,
            chunk_id=msg.get('chunk_id'),
            data=msg.get('data'),
            exclude_socket=client_socket
        )
    
    def handle_file_ack(self, client_socket, msg):
        """Handle FILE_ACK from receiver (forward to sender)"""
        # In this architecture, ACKs go back through server
        # Implementation depends on file transfer design
        pass
    
    def handle_file_end(self, client_socket, msg):
        """Handle FILE_END message"""
        client_info = self.meeting_manager.get_client_info(client_socket)
        if not client_info:
            return
        
        meeting_code = client_info['meeting']
        
        # Notify all participants
        self.broadcast_to_meeting(
            meeting_code,
            MSG_FILE_END_NOTIFY,
            sender_name=client_info['name'],
            checksum=msg.get('checksum'),
            exclude_socket=client_socket
        )
    
    def handle_video_stats(self, client_socket, msg):
        """Handle VIDEO_STATS from receiver"""
        # Stats from receiver about video quality
        # Can be forwarded to sender for adaptive streaming
        client_info = self.meeting_manager.get_client_info(client_socket)
        if not client_info:
            return
        
        # Forward stats update (implementation depends on architecture)
        # For now, just log
        print(f"[ControlHandler] Video stats from {client_info['name']}: "
              f"loss={msg.get('loss')}%, rtt={msg.get('rtt')}ms")
    
    def handle_leave(self, client_socket, msg):
        """Handle LEAVE message"""
        client_info = self.meeting_manager.get_client_info(client_socket)
        if client_info:
            meeting_code = client_info['meeting']
            participant_name = client_info['name']
            
            # Broadcast that participant left
            self.broadcast_to_meeting(
                meeting_code,
                MSG_PARTICIPANT_LEFT,
                participant_name=participant_name,
                exclude_socket=client_socket
            )
        
        self.meeting_manager.leave_meeting(client_socket)
    
    def handle_heartbeat(self, client_socket, msg):
        """Handle HEARTBEAT message"""
        response = pack_tcp_message(MSG_HEARTBEAT_ACK)
        try:
            client_socket.sendall(response)
        except:
            pass
    
    def handle_register_udp(self, client_socket, msg):
        """Handle REGISTER_UDP - register client's UDP receiving ports"""
        print(f"[ControlHandler] handle_register_udp called")
        video_port = msg.get('video_port')
        audio_port = msg.get('audio_port')
        print(f"[ControlHandler] Received UDP registration - video_port: {video_port}, audio_port: {audio_port}")
        
        client_info = self.meeting_manager.get_client_info(client_socket)
        if client_info:
            # Get client's IP from TCP socket
            client_ip = client_socket.getpeername()[0]
            udp_addr = (client_ip, video_port)
            
            # Update UDP address in meeting manager
            self.meeting_manager.update_udp_address(client_socket, udp_addr)
            print(f"[ControlHandler] Registered UDP for {client_info['name']}: {udp_addr}")
        else:
            print(f"[ControlHandler] No client info found for socket")
    
    def broadcast_to_meeting(self, meeting_code, msg_type, exclude_socket=None, **kwargs):
        """Broadcast a message to all participants in a meeting"""
        participants = self.meeting_manager.get_meeting_participants(meeting_code)
        message = pack_tcp_message(msg_type, **kwargs)
        
        for participant_socket in participants:
            if participant_socket != exclude_socket:
                try:
                    participant_socket.sendall(message)
                except Exception as e:
                    print(f"[ControlHandler] Failed to send to participant: {e}")
    
    def stop(self):
        """Stop the control handler"""
        self.running = False
