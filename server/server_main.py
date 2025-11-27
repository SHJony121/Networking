"""
Server Main - Entry point for the server
Handles TCP control connections and coordinates UDP relay
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import socket
import threading
from meeting_manager import MeetingManager
from control_handler import ControlHandler
from stream_relay_udp import StreamRelayUDP
from congestion_control import FileManager

class Server:
    """Main server class"""
    
    def __init__(self, tcp_host='0.0.0.0', tcp_port=5000, udp_port=5001):
        self.tcp_host = tcp_host
        self.tcp_port = tcp_port
        self.udp_port = udp_port
        
        # Core components
        self.meeting_manager = MeetingManager()
        self.file_manager = FileManager()
        self.control_handler = ControlHandler(self.meeting_manager, self.file_manager)
        self.stream_relay = StreamRelayUDP(self.meeting_manager, udp_port)
        
        # Sockets
        self.tcp_socket = None
        self.running = False
    
    def start(self):
        """Start the server"""
        print("=" * 60)
        print("Multi-Client Real-Time Communication Server")
        print("=" * 60)
        
        # Start UDP relay in separate thread
        udp_thread = threading.Thread(target=self.stream_relay.start, daemon=True)
        udp_thread.start()
        print(f"[Server] UDP relay started on port {self.udp_port}")
        
        # Start TCP control server
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.tcp_socket.bind((self.tcp_host, self.tcp_port))
        self.tcp_socket.listen(10)
        
        print(f"[Server] TCP control server listening on {self.tcp_host}:{self.tcp_port}")
        print(f"[Server] Server is ready! Waiting for clients...")
        print("=" * 60)
        
        self.running = True
        
        try:
            while self.running:
                try:
                    client_socket, client_addr = self.tcp_socket.accept()
                    
                    # Handle each client in a separate thread
                    client_thread = threading.Thread(
                        target=self.control_handler.handle_client,
                        args=(client_socket, client_addr),
                        daemon=True
                    )
                    client_thread.start()
                
                except Exception as e:
                    if self.running:
                        print(f"[Server] Error accepting connection: {e}")
        
        except KeyboardInterrupt:
            print("\n[Server] Shutting down...")
        
        finally:
            self.stop()
    
    def stop(self):
        """Stop the server"""
        self.running = False
        self.control_handler.stop()
        self.stream_relay.stop()
        
        if self.tcp_socket:
            try:
                self.tcp_socket.close()
            except:
                pass
        
        print("[Server] Server stopped")

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Real-Time Communication Server')
    parser.add_argument('--host', default='0.0.0.0', help='TCP host address (default: 0.0.0.0)')
    parser.add_argument('--tcp-port', type=int, default=5000, help='TCP control port (default: 5000)')
    parser.add_argument('--udp-port', type=int, default=5001, help='UDP streaming port (default: 5001)')
    
    args = parser.parse_args()
    
    server = Server(tcp_host=args.host, tcp_port=args.tcp_port, udp_port=args.udp_port)
    server.start()

if __name__ == '__main__':
    main()
