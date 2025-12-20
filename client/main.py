"""
Main Client Application - Integrates all components
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtWidgets import QApplication, QStackedWidget, QMessageBox
from PyQt5.QtCore import QThread, pyqtSignal

from ui_home import HomeScreen
from ui_waiting_room import WaitingRoomScreen
from ui_meeting import MeetingScreen
from stats_window import StatsWindow
from tcp_control import ClientSession
from video_sender import VideoSender
from video_receiver import VideoReceiver
from audio_sender import AudioSender
from audio_receiver import AudioReceiver
from stats_collector import StatsCollector
from tcp_file_transfer import TCPFileTransfer, FileReceiver

from common.protocol import *

class ClientApplication(QStackedWidget):
    """Main client application"""
    
    # Signal for thread-safe join request handling
    join_request_signal = pyqtSignal(str)  # client_name
    participant_joined_signal = pyqtSignal(str)  # participant_name
    
    def __init__(self, server_host='127.0.0.1', server_tcp_port=5000, server_udp_port=5001):
        super().__init__()
        
        self.server_host = server_host
        self.server_tcp_port = server_tcp_port
        self.server_udp_port = server_udp_port
        
        # Session
        self.session = None
        self.client_name = None
        self.is_host = False
        self.camera_enabled = True
        self.mic_enabled = True
        
        # Streaming components
        self.video_sender = None
        self.video_receiver = None
        self.audio_sender = None
        self.audio_receiver = None
        self.stats_collector = None
        
        # Connect signals to main-thread handlers
        self.join_request_signal.connect(self._handle_join_request_ui)
        self.participant_joined_signal.connect(self._handle_participant_joined_ui)
        self.file_transfer = None
        self.file_receiver = None
        
        # UI screens
        self.home_screen = HomeScreen()
        self.waiting_room = None
        self.meeting_screen = None
        self.stats_window = None
        
        # Setup UI
        self.setup_ui()
        
        # Connect internal signals
        self.join_request_signal.connect(self._handle_join_request_ui)
        
    def setup_ui(self):
        """Setup UI and connect signals"""
        self.setWindowTitle("Real-Time Communication Client")
        
        # Add home screen
        self.addWidget(self.home_screen)
        
        # Connect home screen signals
        self.home_screen.start_meeting_signal.connect(self.on_start_meeting)
        self.home_screen.join_meeting_signal.connect(self.on_join_meeting)
        
        # Show home screen
        self.setCurrentWidget(self.home_screen)
        self.resize(600, 400)
    
    def on_start_meeting(self, name, camera_enabled, mic_enabled):
        """Handle start meeting"""
        self.client_name = name
        self.is_host = True
        self.camera_enabled = camera_enabled
        self.mic_enabled = mic_enabled
        
        # Connect to server
        self.session = ClientSession(self.server_host, self.server_tcp_port)
        if not self.session.connect():
            QMessageBox.critical(self, "Error", "Failed to connect to server")
            return
        
        # Register handlers FIRST (including for participants joining)
        self.session.tcp_control.register_handler(MSG_CHAT_BROADCAST, self.on_chat_received)
        self.session.tcp_control.register_handler(MSG_PARTICIPANT_JOINED, self.on_participant_joined)
        self.session.tcp_control.register_handler(MSG_PARTICIPANT_LEFT, self.on_participant_left)
        self.session.tcp_control.register_handler(MSG_NEW_JOIN_REQUEST, self.on_new_join_request)
        
        # Create meeting
        meeting_code = self.session.create_meeting(name)
        if not meeting_code:
            QMessageBox.critical(self, "Error", "Failed to create meeting")
            return
        
        # Show waiting room
        self.waiting_room = WaitingRoomScreen(meeting_code)
        self.waiting_room.allow_participant_signal.connect(self.on_allow_participant)
        self.waiting_room.deny_participant_signal.connect(self.on_deny_participant)
        self.waiting_room.start_meeting_signal.connect(self.on_enter_meeting)
        
        self.addWidget(self.waiting_room)
        self.setCurrentWidget(self.waiting_room)
        self.resize(600, 500)
    
    def on_join_meeting(self, meeting_code, name, camera_enabled, mic_enabled):
        """Handle join meeting"""
        self.client_name = name
        self.is_host = False
        self.camera_enabled = camera_enabled
        self.mic_enabled = mic_enabled
        
        # Connect to server
        self.session = ClientSession(self.server_host, self.server_tcp_port)
        if not self.session.connect():
            QMessageBox.critical(self, "Error", "Failed to connect to server")
            return
        
        # Register handlers FIRST (before joining, so we catch messages)
        self.session.tcp_control.register_handler(MSG_CHAT_BROADCAST, self.on_chat_received)
        self.session.tcp_control.register_handler(MSG_PARTICIPANT_JOINED, self.on_participant_joined)
        self.session.tcp_control.register_handler(MSG_PARTICIPANT_LEFT, self.on_participant_left)
        
        # Now join meeting
        QMessageBox.information(self, "Joining", "Requesting to join meeting...")
        
        if self.session.join_meeting(meeting_code, name):
            QMessageBox.information(self, "Success", "Joined meeting!")
            self.on_enter_meeting()
        else:
            QMessageBox.critical(self, "Error", "Failed to join meeting")
    
    def on_new_join_request(self, msg):
        """Handle new join request notification (called from TCP thread)"""
        client_name = msg.get('client_name')
        # Emit signal to handle in main thread
        self.join_request_signal.emit(client_name)
    
    def _handle_join_request_ui(self, client_name):
        """Handle join request in main Qt thread"""
        if not self.is_host:
            return
        
        # Show dialog to approve/deny
        from PyQt5.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self,
            "Join Request",
            f"{client_name} wants to join the meeting.\nAllow them to join?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.Yes:
            print(f"[Client] Approving join request from {client_name}")
            if self.session:
                self.session.allow_participant(client_name)
        else:
            print(f"[Client] Denying join request from {client_name}")
            if self.session:
                self.session.deny_participant(client_name)
    
    def on_allow_participant(self, participant_name):
        """Allow a participant"""
        print(f"[Client] Allowing participant: {participant_name}")
        if self.session:
            self.session.allow_participant(participant_name)
    
    def on_deny_participant(self, participant_name):
        """Deny a participant"""
        if self.session:
            self.session.deny_participant(participant_name)
    
    def on_enter_meeting(self):
        """Enter the meeting room"""
        # Create meeting screen
        self.meeting_screen = MeetingScreen()
        self.meeting_screen.set_mic_state(self.mic_enabled)
        self.meeting_screen.set_camera_state(self.camera_enabled)
        
        # Connect signals
        self.meeting_screen.send_chat_signal.connect(self.on_send_chat)
        self.meeting_screen.send_file_signal.connect(self.on_send_file)
        self.meeting_screen.toggle_mic_signal.connect(self.on_toggle_mic)
        self.meeting_screen.toggle_camera_signal.connect(self.on_toggle_camera)
        self.meeting_screen.leave_meeting_signal.connect(self.on_leave_meeting)
        self.meeting_screen.show_stats_signal.connect(self.on_show_stats)
        
        # Connect frame update to timer
        self.meeting_screen.timer.timeout.disconnect()  # Disconnect old connection
        self.meeting_screen.timer.timeout.connect(self.update_video_frames)  # Connect to our method
        
        # Add own video box
        self.meeting_screen.add_video_stream('self', self.client_name)
        
        # Add any buffered participants that joined before meeting screen was ready
        if hasattr(self, 'pending_participants'):
            print(f"[Client] Adding {len(self.pending_participants)} buffered participants")
            for participant_name in self.pending_participants:
                self.meeting_screen.add_video_stream(participant_name, participant_name)
            self.pending_participants = []
        self.session.tcp_control.register_handler(MSG_CHAT_BROADCAST, self.on_chat_received)
        self.session.tcp_control.register_handler(MSG_PARTICIPANT_JOINED, self.on_participant_joined)
        self.session.tcp_control.register_handler(MSG_PARTICIPANT_LEFT, self.on_participant_left)
        
        self.addWidget(self.meeting_screen)
        self.setCurrentWidget(self.meeting_screen)
        self.resize(1400, 900)
        
        # Initialize streaming components AFTER UI is ready
        self.init_streaming()
    
    def init_streaming(self):
        """Initialize video/audio streaming"""
        # Video sender - allow setting camera index via environment variable
        # Set CAMERA_INDEX environment variable before starting client, default is 0
        # For example: set CAMERA_INDEX=1 (for iVCam on Windows)
        import os
        camera_index = int(os.environ.get('CAMERA_INDEX', 0))
        print(f"[Client] Using camera index: {camera_index}")
        
        self.video_sender = VideoSender(self.server_host, self.server_udp_port, camera_index=camera_index)
        if self.camera_enabled:
            self.video_sender.start()
        else:
            # Still need to create sender but don't open camera
            print("[Client] Camera disabled, not starting video capture")
        
        # Video receiver (use port 0 to let OS assign a free port)
        self.video_receiver = VideoReceiver(0)
        self.video_receiver.start()
        print(f"[Client] Video receiver listening on port {self.video_receiver.local_udp_port}")
        
        # Audio sender
        self.audio_sender = AudioSender(self.server_host, self.server_udp_port)
        self.audio_sender.start()
        self.audio_sender.set_enabled(self.mic_enabled)
        
        # Audio receiver (use port 0 to let OS assign a free port)
        self.audio_receiver = AudioReceiver(0)
        self.audio_receiver.start()
        print(f"[Client] Audio receiver listening on port {self.audio_receiver.local_udp_port}")
        
        # Stats collector
        self.stats_collector = StatsCollector(
            self.video_sender,
            self.video_receiver,
            self.audio_sender,
            self.audio_receiver,
            self.session.tcp_control
        )
        self.stats_collector.start()
        
        # File transfer
        self.file_transfer = TCPFileTransfer(self.session.tcp_control)
        self.file_receiver = FileReceiver()
        
        # Register UDP ports with server
        try:
            print(f"[Client] About to register UDP ports: video={self.video_receiver.local_udp_port}, audio={self.audio_receiver.local_udp_port}")
            self.session.register_udp_ports(
                self.video_receiver.local_udp_port,
                self.audio_receiver.local_udp_port
            )
            print("[Client] UDP ports registered successfully")
            print(f"[Client] Waiting 1 second for server to process registration...")
            import time
            time.sleep(1)  # Give server time to register ports
        except Exception as e:
            print(f"[Client] Failed to register UDP ports: {e}")
            import traceback
            traceback.print_exc()
        
        print("[Client] Streaming initialized")
    
    def update_video_frames(self):
        """Update video frames in meeting screen"""
        if not self.meeting_screen:
            return
        
        # Update own video from video sender's latest frame (only if camera is enabled)
        if self.video_sender and self.camera_enabled:
            frame = self.video_sender.get_latest_frame()
            if frame is not None:
                self.meeting_screen.update_video_frame('self', frame)
        
        # Update received video streams for other participants
        if self.video_receiver:
            sender_frames = self.video_receiver.get_all_sender_frames()
            
            # Get list of other participants (not self)
            other_participants = [pid for pid in self.meeting_screen.video_widgets.keys() if pid != 'self']
            
            # Assign received frames to participant boxes
            frame_list = list(sender_frames.values())
            
            # Only update if we have frames AND participants
            if frame_list and other_participants:
                # For now, just show the latest received frame in the first participant box
                # (This is a limitation - we can't distinguish which frame belongs to which participant
                # without proper UDP address mapping, which requires REGISTER_UDP to work properly)
                for idx, participant_id in enumerate(other_participants):
                    if idx < len(frame_list):
                        self.meeting_screen.update_video_frame(participant_id, frame_list[idx])
    
    def on_send_chat(self, message):
        """Send chat message"""
        if self.session:
            self.session.send_chat(message)
            # Add to own chat (only if not host, host sees broadcast)
            if not self.is_host:
                self.meeting_screen.add_chat_message(self.client_name, message)
    
    def on_chat_received(self, msg):
        """Handle received chat message"""
        sender_name = msg.get('sender_name')
        message = msg.get('message')
        if self.meeting_screen and sender_name != self.client_name:
            self.meeting_screen.add_chat_message(sender_name, message)
    
    def on_send_file(self, filepath):
        """Send file"""
        if self.file_transfer:
            import threading
            thread = threading.Thread(
                target=self.file_transfer.send_file,
                args=(filepath,),
                daemon=True
            )
            thread.start()
    
    def on_toggle_mic(self, enabled):
        """Toggle microphone"""
        self.mic_enabled = enabled
        if self.audio_sender:
            self.audio_sender.set_enabled(enabled)
    
    def on_toggle_camera(self, enabled):
        """Toggle camera"""
        self.camera_enabled = enabled
        if self.video_sender:
            self.video_sender.set_enabled(enabled)
        
        # Clear video display when camera is turned off
        if not enabled and self.meeting_screen:
            self.meeting_screen.clear_video_frame('self')
    
    def on_show_stats(self):
        """Show statistics window"""
        if self.stats_collector:
            self.stats_window = StatsWindow(self.stats_collector, self.file_transfer)
            self.stats_window.show()
    
    def on_participant_joined(self, msg):
        """Handle participant joined (called from TCP thread)"""
        participant_name = msg.get('participant_name')
        print(f"[Client] PARTICIPANT_JOINED received: {participant_name}, my name: {self.client_name}")
        
        # Don't add yourself again
        if participant_name == self.client_name:
            print(f"[Client] Skipping own name")
            return
        
        # Emit signal to handle in main Qt thread
        self.participant_joined_signal.emit(participant_name)
    
    def _handle_participant_joined_ui(self, participant_name):
        """Handle participant joined in main Qt thread"""
        if self.meeting_screen:
            print(f"[Client] Adding video box for {participant_name}")
            print(f"[Client] Current video_widgets BEFORE add: {list(self.meeting_screen.video_widgets.keys())}")
            self.meeting_screen.add_video_stream(participant_name, participant_name)
            print(f"[Client] Current video_widgets AFTER add: {list(self.meeting_screen.video_widgets.keys())}")
            self.meeting_screen.add_chat_message("System", f"{participant_name} joined")
        else:
            # Buffer participants that joined before meeting screen was created
            print(f"[Client] Buffering participant {participant_name} (meeting screen not ready yet)")
            if not hasattr(self, 'pending_participants'):
                self.pending_participants = []
            self.pending_participants.append(participant_name)
    
    def on_participant_left(self, msg):
        """Handle participant left"""
        participant_name = msg.get('participant_name')
        if self.meeting_screen:
            self.meeting_screen.remove_video_stream(participant_name)
            self.meeting_screen.add_chat_message("System", f"{participant_name} left")
    
    def on_leave_meeting(self):
        """Leave meeting"""
        print("[Client] Leaving meeting...")
        
        # Stop the video update timer
        if self.meeting_screen and hasattr(self.meeting_screen, 'timer'):
            self.meeting_screen.timer.stop()
            print("[Client] Timer stopped")
        
        # Stop streaming
        if self.video_sender:
            self.video_sender.stop()
        if self.video_receiver:
            self.video_receiver.stop()
        if self.audio_sender:
            self.audio_sender.stop()
        if self.audio_receiver:
            self.audio_receiver.stop()
        if self.stats_collector:
            self.stats_collector.stop()
        
        # Disconnect session
        if self.session:
            self.session.disconnect()
        
        # Return to home
        self.setCurrentWidget(self.home_screen)
        self.resize(600, 400)
        
        QMessageBox.information(self, "Left", "You have left the meeting")

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Real-Time Communication Client')
    parser.add_argument('--server', default='127.0.0.1', help='Server address (default: 127.0.0.1)')
    parser.add_argument('--tcp-port', type=int, default=5000, help='Server TCP port (default: 5000)')
    parser.add_argument('--udp-port', type=int, default=5001, help='Server UDP port (default: 5001)')
    parser.add_argument('--camera', type=int, help='Camera index (e.g., 0 for laptop, 1 for iVCam)')
    
    args = parser.parse_args()
    
    # Set camera index if provided via command line
    if args.camera is not None:
        os.environ['CAMERA_INDEX'] = str(args.camera)
        print(f"[Main] Camera index set to: {args.camera}")
    
    app = QApplication(sys.argv)
    client = ClientApplication(
        server_host=args.server,
        server_tcp_port=args.tcp_port,
        server_udp_port=args.udp_port
    )
    client.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
