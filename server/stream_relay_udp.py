"""
Stream Relay UDP - Handles video and audio stream relaying
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import socket
import threading
from common.protocol import *

class StreamRelayUDP:
    """Relays video and audio UDP packets between clients"""
    
    def __init__(self, meeting_manager, udp_port):
        self.meeting_manager = meeting_manager
        self.udp_port = udp_port
        self.socket = None
        self.running = False
        
        # Track UDP addresses for clients
        # {client_udp_addr: client_socket}
        self.udp_to_socket = {}
    
    def start(self):
        """Start the UDP relay server"""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(('0.0.0.0', self.udp_port))
        self.running = True
        
        print(f"[StreamRelay] UDP relay listening on port {self.udp_port}")
        
        while self.running:
            try:
                data, addr = self.socket.recvfrom(65535)  # Max UDP packet size
                
                # Handle packet in separate thread to avoid blocking
                threading.Thread(
                    target=self.handle_packet,
                    args=(data, addr),
                    daemon=True
                ).start()
            
            except Exception as e:
                if self.running:
                    print(f"[StreamRelay] Error receiving packet: {e}")
    
    def handle_packet(self, data, sender_addr):
        """Handle incoming UDP packet and relay to appropriate recipients"""
        try:
            # Determine packet type (video or audio) by header size
            if len(data) >= VIDEO_HEADER_SIZE:
                # Try to parse as video packet
                try:
                    header = unpack_video_header(data)
                    self.relay_video_packet(data, sender_addr)
                    return
                except:
                    pass
            
            if len(data) >= AUDIO_HEADER_SIZE:
                # Try to parse as audio packet
                try:
                    header = unpack_audio_header(data)
                    self.relay_audio_packet(data, sender_addr)
                    return
                except:
                    pass
            
            # Unknown packet type
            print(f"[StreamRelay] Unknown packet type from {sender_addr}")
        
        except Exception as e:
            print(f"[StreamRelay] Error handling packet from {sender_addr}: {e}")
    
    def relay_video_packet(self, data, sender_addr):
        """Relay video packet to all participants in the same meeting"""
        # Find sender's meeting
        client_socket = self.find_client_by_udp_addr(sender_addr)
        if not client_socket:
            # First packet from this client, try to register
            self.register_udp_addr(sender_addr)
            client_socket = self.find_client_by_udp_addr(sender_addr)
            if not client_socket:
                return
        
        client_info = self.meeting_manager.get_client_info(client_socket)
        if not client_info:
            return
        
        meeting_code = client_info['meeting']
        
        # Get all participants in the meeting
        participants = self.meeting_manager.get_meeting_participants(meeting_code)
        
        # Relay to all participants except sender
        for participant_socket in participants:
            if participant_socket != client_socket:
                participant_info = self.meeting_manager.get_client_info(participant_socket)
                if participant_info and participant_info.get('udp_addr'):
                    try:
                        self.socket.sendto(data, participant_info['udp_addr'])
                    except Exception as e:
                        print(f"[StreamRelay] Failed to relay video to {participant_info['udp_addr']}: {e}")
    
    def relay_audio_packet(self, data, sender_addr):
        """Relay audio packet to all participants in the same meeting"""
        # Similar to video relay
        client_socket = self.find_client_by_udp_addr(sender_addr)
        if not client_socket:
            self.register_udp_addr(sender_addr)
            client_socket = self.find_client_by_udp_addr(sender_addr)
            if not client_socket:
                return
        
        client_info = self.meeting_manager.get_client_info(client_socket)
        if not client_info:
            return
        
        meeting_code = client_info['meeting']
        participants = self.meeting_manager.get_meeting_participants(meeting_code)
        
        # Relay to all participants except sender
        for participant_socket in participants:
            if participant_socket != client_socket:
                participant_info = self.meeting_manager.get_client_info(participant_socket)
                if participant_info and participant_info.get('udp_addr'):
                    try:
                        self.socket.sendto(data, participant_info['udp_addr'])
                    except Exception as e:
                        print(f"[StreamRelay] Failed to relay audio to {participant_info['udp_addr']}: {e}")
    
    def find_client_by_udp_addr(self, udp_addr):
        """Find client socket by UDP address"""
        # Search through all clients to find matching UDP address
        for client_socket, client_info in self.meeting_manager.client_info.items():
            if client_info.get('udp_addr') == udp_addr:
                return client_socket
        return None
    
    def register_udp_addr(self, udp_addr):
        """Register a new UDP address (called on first packet)"""
        # This is a simplified registration - in production, clients should
        # send their UDP address through TCP control channel first
        print(f"[StreamRelay] New UDP address detected: {udp_addr}")
        # The client should have already registered via TCP, so we just
        # update the UDP address in meeting_manager
        # This is handled when client sends first packet
    
    def stop(self):
        """Stop the UDP relay"""
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        print("[StreamRelay] UDP relay stopped")
