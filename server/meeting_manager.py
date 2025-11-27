"""
Meeting Manager - Handles meeting state and participant management
"""
import random
import string
import threading
from typing import Dict, List, Optional, Tuple

class MeetingManager:
    """Manages all meetings, participants, and join requests"""
    
    def __init__(self):
        self.lock = threading.Lock()
        
        # meetings = {
        #     "<meeting_code>": {
        #         "host": <client_socket>,
        #         "participants": [<client_socket>, ...],
        #         "waiting": [<client_socket>, ...]
        #     }
        # }
        self.meetings: Dict[str, Dict] = {}
        
        # client_info = {
        #     <client_socket>: {
        #         "name": "Jony",
        #         "meeting": "482913",
        #         "is_host": True/False,
        #         "udp_addr": (ip, port)
        #     }
        # }
        self.client_info: Dict = {}
        
        # Socket to address mapping for reverse lookup
        self.socket_to_addr: Dict = {}
    
    def generate_meeting_code(self) -> str:
        """Generate a random 6-digit meeting code"""
        while True:
            code = ''.join(random.choices(string.digits, k=6))
            with self.lock:
                if code not in self.meetings:
                    return code
    
    def create_meeting(self, host_socket, host_name: str) -> str:
        """
        Create a new meeting with the given host
        Returns: meeting_code
        """
        meeting_code = self.generate_meeting_code()
        
        with self.lock:
            self.meetings[meeting_code] = {
                'host': host_socket,
                'participants': [host_socket],
                'waiting': []
            }
            
            self.client_info[host_socket] = {
                'name': host_name,
                'meeting': meeting_code,
                'is_host': True,
                'udp_addr': None
            }
        
        print(f"[MeetingManager] Meeting {meeting_code} created by {host_name}")
        return meeting_code
    
    def request_join(self, client_socket, meeting_code: str, client_name: str) -> Tuple[bool, str]:
        """
        Request to join a meeting
        Returns: (success, message)
        """
        with self.lock:
            if meeting_code not in self.meetings:
                return False, "Meeting not found"
            
            meeting = self.meetings[meeting_code]
            
            # Add to waiting list
            if client_socket not in meeting['waiting']:
                meeting['waiting'].append(client_socket)
            
            # Store client info
            self.client_info[client_socket] = {
                'name': client_name,
                'meeting': meeting_code,
                'is_host': False,
                'udp_addr': None
            }
        
        print(f"[MeetingManager] {client_name} requested to join {meeting_code}")
        return True, "Join request sent to host"
    
    def allow_join(self, client_socket) -> bool:
        """
        Host allows a waiting client to join
        Returns: success
        """
        with self.lock:
            client_data = self.client_info.get(client_socket)
            if not client_data:
                return False
            
            meeting_code = client_data['meeting']
            meeting = self.meetings.get(meeting_code)
            
            if not meeting:
                return False
            
            # Move from waiting to participants
            if client_socket in meeting['waiting']:
                meeting['waiting'].remove(client_socket)
            
            if client_socket not in meeting['participants']:
                meeting['participants'].append(client_socket)
            
        print(f"[MeetingManager] {client_data['name']} joined meeting {meeting_code}")
        return True
    
    def deny_join(self, client_socket) -> bool:
        """
        Host denies a waiting client
        Returns: success
        """
        with self.lock:
            client_data = self.client_info.get(client_socket)
            if not client_data:
                return False
            
            meeting_code = client_data['meeting']
            meeting = self.meetings.get(meeting_code)
            
            if not meeting:
                return False
            
            # Remove from waiting list
            if client_socket in meeting['waiting']:
                meeting['waiting'].remove(client_socket)
            
            # Remove client info
            del self.client_info[client_socket]
        
        print(f"[MeetingManager] Join request denied for meeting {meeting_code}")
        return True
    
    def leave_meeting(self, client_socket):
        """Remove a client from their meeting"""
        with self.lock:
            client_data = self.client_info.get(client_socket)
            if not client_data:
                return
            
            meeting_code = client_data['meeting']
            meeting = self.meetings.get(meeting_code)
            
            if meeting:
                # Remove from participants or waiting
                if client_socket in meeting['participants']:
                    meeting['participants'].remove(client_socket)
                if client_socket in meeting['waiting']:
                    meeting['waiting'].remove(client_socket)
                
                # If host left, close the meeting
                if meeting['host'] == client_socket:
                    print(f"[MeetingManager] Host left, closing meeting {meeting_code}")
                    del self.meetings[meeting_code]
                    # Clean up all clients in this meeting
                    clients_to_remove = [sock for sock, info in self.client_info.items() 
                                        if info['meeting'] == meeting_code]
                    for sock in clients_to_remove:
                        if sock in self.client_info:
                            del self.client_info[sock]
                elif len(meeting['participants']) == 0:
                    # No participants left, clean up
                    del self.meetings[meeting_code]
            
            # Remove client info
            if client_socket in self.client_info:
                del self.client_info[client_socket]
        
        print(f"[MeetingManager] Client left meeting {meeting_code}")
    
    def set_udp_addr(self, client_socket, udp_addr: Tuple[str, int]):
        """Set the UDP address for a client"""
        with self.lock:
            if client_socket in self.client_info:
                self.client_info[client_socket]['udp_addr'] = udp_addr
    
    def get_meeting_info(self, meeting_code: str) -> Optional[Dict]:
        """Get meeting information"""
        with self.lock:
            return self.meetings.get(meeting_code)
    
    def get_client_info(self, client_socket) -> Optional[Dict]:
        """Get client information"""
        with self.lock:
            return self.client_info.get(client_socket)
    
    def update_udp_address(self, client_socket, udp_addr):
        """Update client's UDP address for stream relay"""
        with self.lock:
            if client_socket in self.client_info:
                self.client_info[client_socket]['udp_addr'] = udp_addr
                print(f"[MeetingManager] Updated UDP address for client: {udp_addr}")
    
    def get_meeting_participants(self, meeting_code: str) -> List:
        """Get list of participant sockets in a meeting"""
        with self.lock:
            meeting = self.meetings.get(meeting_code)
            if meeting:
                return meeting['participants'].copy()
            return []
    
    def get_waiting_list(self, meeting_code: str) -> List[Dict]:
        """Get list of waiting clients with their info"""
        with self.lock:
            meeting = self.meetings.get(meeting_code)
            if not meeting:
                return []
            
            waiting_info = []
            for client_socket in meeting['waiting']:
                client_data = self.client_info.get(client_socket)
                if client_data:
                    waiting_info.append({
                        'socket': client_socket,
                        'name': client_data['name']
                    })
            return waiting_info
    
    def is_host(self, client_socket) -> bool:
        """Check if client is a host"""
        with self.lock:
            client_data = self.client_info.get(client_socket)
            return client_data.get('is_host', False) if client_data else False
    
    def get_host_socket(self, meeting_code: str):
        """Get the host socket for a meeting"""
        with self.lock:
            meeting = self.meetings.get(meeting_code)
            return meeting['host'] if meeting else None
