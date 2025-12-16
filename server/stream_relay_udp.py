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
        
        # Track UDP sending addresses: {sender_addr: last_seen_time}
        self.active_udp_addresses = {}
        self.udp_lock = threading.Lock()
    
    def start(self):
        """Start the UDP relay server"""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(('0.0.0.0', self.udp_port))
        self.running = True
        
        print(f"[StreamRelay] UDP relay listening on port {self.udp_port}")
        print(f"[StreamRelay] Socket bound to {self.socket.getsockname()}")
        
        packet_count = 0
        while self.running:
            try:
                data, addr = self.socket.recvfrom(65535)  # Max UDP packet size
                packet_count += 1
                
                if packet_count % 100 == 0:  # Log every 100 packets
                    print(f"[StreamRelay] Received {packet_count} UDP packets")
                
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
        """Relay video packet to ALL other clients' REGISTERED receiver addresses"""
        import time
        
        # Track sender as active
        with self.udp_lock:
            self.active_udp_addresses[sender_addr] = time.time()
        
        # Find which client is sending (by matching IP)
        sender_ip = sender_addr[0]
        sender_client_socket = None
        
        for client_socket, client_info in self.meeting_manager.client_info.items():
            udp_addr = client_info.get('udp_addr')
            if udp_addr and udp_addr[0] == sender_ip:
                # Check if sender port is close to registered port (within 10 ports)
                port_diff = abs(udp_addr[1] - sender_addr[1])
                if port_diff < 10:  # Same client (sender/receiver ports are close)
                    sender_client_socket = client_socket
                    break
        
        # Get ALL registered UDP addresses EXCEPT the sender
        recipient_addrs = []
        for client_socket, client_info in self.meeting_manager.client_info.items():
            if client_socket == sender_client_socket:
                continue  # Skip sender
            
            udp_addr = client_info.get('udp_addr')
            if udp_addr:
                recipient_addrs.append((udp_addr, client_info.get('name', 'unknown')))
        
        print(f"[StreamRelay] Video from {sender_addr}, relaying to {len(recipient_addrs)} registered receivers (excluding sender)")
        
        # Relay to registered receiver addresses
        for udp_addr, name in recipient_addrs:
            try:
                self.socket.sendto(data, udp_addr)
            except Exception as e:
                print(f"[StreamRelay] Failed to relay video to {name} at {udp_addr}: {e}")
        
        if len(recipient_addrs) == 0:
            print(f"[StreamRelay] WARNING: No registered recipients to relay video to!")
    
    def relay_audio_packet(self, data, sender_addr):
        """Relay audio packet to ALL other clients' REGISTERED receiver addresses"""
        import time
        
        # Track sender as active
        with self.udp_lock:
            self.active_udp_addresses[sender_addr] = time.time()
        
        # Get ALL registered UDP addresses from meeting_manager
        recipient_addrs = []
        for client_socket, client_info in self.meeting_manager.client_info.items():
            udp_addr = client_info.get('udp_addr')
            if udp_addr and udp_addr != sender_addr:  # Don't send back to sender
                recipient_addrs.append(udp_addr)
        
        # Relay to registered receiver addresses
        for udp_addr in recipient_addrs:
            try:
                self.socket.sendto(data, udp_addr)
            except Exception as e:
                print(f"[StreamRelay] Failed to relay audio to {udp_addr}: {e}")
    
    def stop(self):
        """Stop the UDP relay"""
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        print("[StreamRelay] UDP relay stopped")
