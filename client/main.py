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
    participant_joined_signal = pyqtSignal(str, bool)  # participant_name, is_host
    
    # File transfer signals
    file_start_signal = pyqtSignal(str, int)  # filename, filesize
    file_chunk_signal = pyqtSignal(int, str)  # chunk_id, data_b64
    file_end_signal = pyqtSignal(str)  # checksum
    chat_signal = pyqtSignal(str, str, bool)  # sender, message, is_private
    camera_status_signal = pyqtSignal(str, bool)  # participant_name, camera_enabled
    quality_changed_signal = pyqtSignal(str) # quality_text
    
    def __init__(self, server_host='127.0.0.1', server_tcp_port=5000, server_udp_port=5001, simulated_loss_rate=0.0):
        super().__init__()
        
        self.server_host = server_host
        self.server_tcp_port = server_tcp_port
        self.server_udp_port = server_udp_port
        self.simulated_loss_rate = simulated_loss_rate
        
        # Session
        self.session = None
        self.client_name = None
        self.is_host = False
        self.camera_enabled = True
        self.mic_enabled = True
        
        # Track camera status of other participants
        # {participant_name: True/False} - True means camera is ON
        self.participant_camera_status = {}
        
        # Streaming components
        self.video_sender = None
        self.video_receiver = None
        self.audio_sender = None
        self.audio_receiver = None
        self.stats_collector = None
        
        # Connect signals to main-thread handlers
        self.join_request_signal.connect(self._handle_join_request_ui)
        self.participant_joined_signal.connect(self._handle_participant_joined_ui)
        self.chat_signal.connect(self._handle_chat_ui)
        self.camera_status_signal.connect(self._handle_camera_status_ui)
        self.quality_changed_signal.connect(self._handle_quality_change_ui)
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
        self.file_start_signal.connect(self._handle_file_start_ui)
        self.file_chunk_signal.connect(self._handle_file_chunk_ui)
        self.file_end_signal.connect(self._handle_file_end_ui)
        
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
        
        # Register handlers FIRST
        self.session.tcp_control.register_handler(MSG_CHAT_BROADCAST, self.on_chat_received)
        self.session.tcp_control.register_handler(MSG_PARTICIPANT_JOINED, self.on_participant_joined)
        self.session.tcp_control.register_handler(MSG_PARTICIPANT_LEFT, self.on_participant_left)
        self.session.tcp_control.register_handler(MSG_NEW_JOIN_REQUEST, self.on_new_join_request)
        
        # Create meeting
        meeting_code = self.session.create_meeting(name)
        if not meeting_code:
            QMessageBox.critical(self, "Error", "Failed to create meeting")
            return
        
        # DIRECT ENTRY: Host enters meeting immediately (Google Meet/Zoom style)
        # Store meeting code for reference
        self.meeting_code = meeting_code
        self.on_enter_meeting()
    
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
        # Now join meeting
        QMessageBox.information(self, "Joining", "Requesting to join meeting...")
        
        if self.session.join_meeting(meeting_code, name):
            QMessageBox.information(self, "Success", "Joined meeting!")
            self.meeting_code = meeting_code # Store for info button
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
        self.meeting_screen.toggle_screen_share_signal.connect(self.on_toggle_screen_share)
        self.meeting_screen.leave_meeting_signal.connect(self.on_leave_meeting)
        self.meeting_screen.show_stats_signal.connect(self.on_show_stats)
        
        # Connect frame update to timer
        self.meeting_screen.timer.timeout.disconnect()  # Disconnect old connection
        self.meeting_screen.timer.timeout.connect(self.update_video_frames)  # Connect to our method
        
        
        # Add self video and update info
        self.meeting_screen.set_meeting_info(getattr(self, 'meeting_code', 'Unknown'), self.client_name)
        self.meeting_screen.add_video_stream('self', self.client_name)
        self.meeting_screen.add_participant_to_list(self.client_name, self.is_host)
        
        # Initialize own camera status (for self)
        self.participant_camera_status['self'] = self.camera_enabled
        print(f"[Client] Initialized own camera status: {self.camera_enabled}")
        
        # Add any buffered participants
        if hasattr(self, 'pending_participants'):
            print(f"[Client] Adding {len(self.pending_participants)} buffered participants")
            for p in self.pending_participants:
                name = p['name']
                is_host = p.get('is_host', False)
                self.meeting_screen.add_video_stream(name, name)
                self.meeting_screen.add_participant_to_list(name, is_host)
                # Initialize camera status for buffered participant
                self.participant_camera_status[name] = True
                print(f"[Client] Initialized buffered participant {name} camera status: ON")
            self.pending_participants = []
            
        self.session.tcp_control.register_handler(MSG_CHAT_BROADCAST, self.on_chat_received)
        self.session.tcp_control.register_handler(MSG_PARTICIPANT_JOINED, self.on_participant_joined)
        self.session.tcp_control.register_handler(MSG_PARTICIPANT_LEFT, self.on_participant_left)
        self.session.tcp_control.register_handler(MSG_CAMERA_STATUS_BROADCAST, self.on_camera_status_received)
        
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
        
        self.video_sender = VideoSender(
            self.server_host, 
            self.server_udp_port, 
            camera_index=camera_index,
            simulated_loss_rate=self.simulated_loss_rate
        )
        if self.camera_enabled:
            self.video_sender.start()
        else:
            # Still need to create sender but don't open camera
            print("[Client] Camera disabled, not starting video capture")
        
        # Connect quality callback
        self.video_sender.quality_callback = self._on_sender_quality_changed
        
        # Video receiver (use port 0 to let OS assign a free port)
        self.video_receiver = VideoReceiver(0, simulated_loss_rate=self.simulated_loss_rate)

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
        self.stats_collector.stats_updated_signal.connect(self._handle_stats_update_ui)
        self.stats_collector.start()
        
        # File transfer
        self.file_transfer = TCPFileTransfer(self.session.tcp_control)
        self.file_receiver = FileReceiver()
        
        # Register file handlers
        self.session.tcp_control.register_handler(MSG_FILE_START_NOTIFY, self.on_file_start)
        self.session.tcp_control.register_handler(MSG_FILE_CHUNK_FORWARD, self.on_file_chunk)
        self.session.tcp_control.register_handler(MSG_FILE_END_NOTIFY, self.on_file_end)
        
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
        
        # Send initial camera status to everyone
        try:
            if self.session and self.session.tcp_control:
                self.session.tcp_control.send_message(
                    MSG_CAMERA_STATUS,
                    enabled=self.camera_enabled
                )
                print(f"[Client] Initial camera status sent: {'ON' if self.camera_enabled else 'OFF'}")
        except Exception as e:
            print(f"[Client] Failed to send initial camera status: {e}")
        
        print("[Client] Streaming initialized")
    
    def update_video_frames(self):
        """Update video frames in meeting screen"""
        if not self.meeting_screen:
            return
        
        # Update own video from video sender's latest frame (only if camera is enabled OR screen sharing)
        if self.video_sender and (self.camera_enabled or self.video_sender.is_screen_sharing):
            frame = self.video_sender.get_latest_frame()
            if frame is not None:
                self.meeting_screen.update_video_frame('self', frame)
        
        # Update received video streams for other participants
        if self.video_receiver:
            sender_frames = self.video_receiver.get_all_sender_frames()
            
            # Get list of other participants (not self) who have camera ON
            all_other_participants = [pid for pid in self.meeting_screen.video_widgets.keys() if pid != 'self']
            participants_with_camera_on = [
                pid for pid in all_other_participants
                if self.participant_camera_status.get(pid, True)  # Default to True (camera ON)
            ]
            
            # Debug logging (only every 60 frames to avoid spam)
            if not hasattr(self, '_frame_update_count'):
                self._frame_update_count = 0
            self._frame_update_count += 1
            if self._frame_update_count % 60 == 0:
                print(f"[Client] update_video_frames: all_participants={all_other_participants}, "
                      f"camera_on={participants_with_camera_on}, "
                      f"camera_status={self.participant_camera_status}")
            
            # Assign received frames to participant boxes with camera ON
            frame_list = list(sender_frames.values())
            
            # Only update if we have frames AND participants with camera ON
            if frame_list and participants_with_camera_on:
                # For now, just show the latest received frame in the first participant box
                # (This is a limitation - we can't distinguish which frame belongs to which participant
                # without proper UDP address mapping, which requires REGISTER_UDP to work properly)
                for idx, participant_id in enumerate(participants_with_camera_on):
                    if idx < len(frame_list):
                        self.meeting_screen.update_video_frame(participant_id, frame_list[idx])
    
    def on_send_chat(self, message_data):
        """Send chat message"""
        if "|||" in message_data:
            message, target = message_data.split("|||", 1)
        else:
            message = message_data
            target = "Everyone"
            
        if self.session:
            self.session.send_chat(message, target)
            # Add to own chat (only if not host, host sees broadcast)
            # Actually, both see broadcast for public, but for private sender needs to see it locally
            if target != "Everyone":
                self.meeting_screen.add_chat_message(self.client_name, f"(to {target}) {message}", is_private=True)
    
    def on_chat_received(self, msg):
        """Handle received chat message"""
        sender_name = msg.get('sender_name')
        message = msg.get('message')
        is_private = msg.get('is_private', False)
        
        # Prevent duplicate private messages (we added it locally with "to Target")
        if is_private and sender_name == self.client_name:
            return
            
        if self.meeting_screen: 
             # For private messages, we might be target OR sender (reflected back)
            self.chat_signal.emit(sender_name, message, is_private)

    def _handle_chat_ui(self, sender, message, is_private):
        """Handle chat in main thread"""
        if self.meeting_screen:
            self.meeting_screen.add_chat_message(sender, message, is_private)
    
    def on_send_file(self, filepath, target="Everyone"):
        """Send file"""
        if self.file_transfer:
            import threading
            thread = threading.Thread(
                target=self.file_transfer.send_file,
                args=(filepath, target),
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
        print(f"[Client] ===== on_toggle_camera called: enabled={enabled} =====")
        self.camera_enabled = enabled
        
        # If camera is enabled, ensure screen share is disabled in sender
        if enabled and self.video_sender:
             self.video_sender.set_screen_sharing(False)
        
        if self.video_sender:
            self.video_sender.set_enabled(enabled)
            print(f"[Client] Video sender enabled set to: {enabled}")
        
        # Notify server about camera status change
        if self.session and self.session.tcp_control:
            try:
                print(f"[Client] About to send camera status message...")
                self.session.tcp_control.send_message(
                    MSG_CAMERA_STATUS,
                    enabled=enabled
                )
                print(f"[Client] Camera status sent: {'ON' if enabled else 'OFF'}")
            except Exception as e:
                print(f"[Client] Failed to send camera status: {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"[Client] WARNING: Cannot send camera status - session={self.session}, tcp_control={self.session.tcp_control if self.session else 'N/A'}")
        
        # Update own video widget to show "(No Video)" when camera is off
        if not enabled and self.meeting_screen:
            print(f"[Client] Showing '(No Video)' for self")
            self.meeting_screen.show_no_video('self', self.client_name)
        
        # Clear video display when camera is turned off
        # if not enabled and self.meeting_screen:
        #    self.meeting_screen.clear_video_frame('self')
        
        print(f"[Client] ===== on_toggle_camera completed =====")

    def on_toggle_screen_share(self, enabled):
        """Toggle screen sharing"""
        print(f"[Client] Screen sharing toggled: {enabled}")
        
        if self.video_sender:
            # enable screen sharing mode
            self.video_sender.set_screen_sharing(enabled)
            
            if enabled:
                # If screen share is ON, we MUST enable the video sender 
                # (even if camera was off)
                self.video_sender.set_enabled(True)
                
                # Also visually update camera button state in UI handled in UI class
                # But we should update our internal state
                self.camera_enabled = False 
                
                # Notify server that "Camera" (Video stream) is ON
                # So others see the screen share
                if self.session and self.session.tcp_control:
                    self.session.tcp_control.send_message(MSG_CAMERA_STATUS, enabled=True)
            else:
                 # If turning OFF screen share, assume we go back to "Camera OFF" state
                 # Unless user explicitly turns camera on. 
                 # For simplicity, turn off video when stopping screen share.
                 self.video_sender.set_enabled(False)
                 if self.session and self.session.tcp_control:
                    self.session.tcp_control.send_message(MSG_CAMERA_STATUS, enabled=False)
                 
                 if self.meeting_screen:
                    self.meeting_screen.show_no_video('self', self.client_name)
    
    def on_show_stats(self):
        """Show statistics window"""
        if self.stats_collector:
            self.stats_window = StatsWindow(self.stats_collector, self.file_transfer)
            self.stats_window.show()
    
    def on_participant_joined(self, msg):
        """Handle participant joined (called from TCP thread)"""
        participant_name = msg.get('participant_name')
        is_host = msg.get('is_host', False)
        print(f"[Client] PARTICIPANT_JOINED received: {participant_name}, host={is_host}")
        
        # Don't add yourself again
        if participant_name == self.client_name:
            print(f"[Client] Skipping own name")
            return
        
        # Emit signal to handle in main Qt thread
        self.participant_joined_signal.emit(participant_name, is_host)
    
    def _handle_participant_joined_ui(self, participant_name, is_host):
        """Handle participant joined in main Qt thread"""
        if self.meeting_screen:
            print(f"[Client] Adding video box for {participant_name}")
            self.meeting_screen.add_video_stream(participant_name, participant_name)
            self.meeting_screen.add_video_stream(participant_name, participant_name)
            
            # Initialize camera status to ON for new participant
            self.participant_camera_status[participant_name] = True
            print(f"[Client] Initialized camera status for {participant_name}: ON")
            
            # Add to list (UI automatically updates combo box now)
            self.meeting_screen.add_participant_to_list(participant_name, is_host)
            
            self.meeting_screen.add_chat_message("System", f"{participant_name} joined")
        else:
            # Buffer participants that joined before meeting screen was created
            print(f"[Client] Buffering participant {participant_name} (meeting screen not ready yet)")
            if not hasattr(self, 'pending_participants'):
                self.pending_participants = []
            self.pending_participants.append({'name': participant_name, 'is_host': is_host})
    
    def on_participant_left(self, msg):
        """Handle participant left"""
        participant_name = msg.get('participant_name')
        if self.meeting_screen:
            self.meeting_screen.remove_video_stream(participant_name)
        if self.meeting_screen:
            self.meeting_screen.remove_video_stream(participant_name)
            self.meeting_screen.remove_participant_from_list(participant_name)
            self.meeting_screen.add_chat_message("System", f"{participant_name} left")
    
    def on_camera_status_received(self, msg):
        """Handle camera status broadcast from another participant"""
        participant_name = msg.get('participant_name')
        enabled = msg.get('enabled', True)
        
        # Skip if it's our own status
        if participant_name == self.client_name:
            return
        
        print(f"[Client] Camera status received: {participant_name} camera {'ON' if enabled else 'OFF'}")
        
        # Emit signal to handle in main thread
        self.camera_status_signal.emit(participant_name, enabled)
    
    def _handle_camera_status_ui(self, participant_name, enabled):
        """Handle camera status in main thread"""
        # Track the camera status
        self.participant_camera_status[participant_name] = enabled
        print(f"[Client] Updated camera status: {participant_name} = {enabled}")
        print(f"[Client] All camera statuses: {self.participant_camera_status}")
        print(f"[Client] Video widgets keys: {list(self.meeting_screen.video_widgets.keys()) if self.meeting_screen else 'No meeting screen'}")
        
        if self.meeting_screen:
            if enabled:
                # Camera is ON - video frames will be received and displayed normally
                print(f"[Client] {participant_name} turned camera ON")
            else:
                # Camera is OFF - show "(No Video)" placeholder
                self.meeting_screen.show_no_video(participant_name, participant_name)
                print(f"[Client] {participant_name} turned camera OFF, showing placeholder")

    def _handle_stats_update_ui(self, stats):
        """Handle stats update in main thread"""
        if self.meeting_screen:
            rtt = stats.get('rtt_ms', 0)
            self.meeting_screen.update_ping(rtt)

    def _on_sender_quality_changed(self, quality_text):
        """Handle quality change from video sender thread"""
        self.quality_changed_signal.emit(quality_text)
        
    def _handle_quality_change_ui(self, quality_text):
        """Handle quality change in UI thread"""
        if self.meeting_screen:
            self.meeting_screen.update_quality_display(quality_text)

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

    # File Transfer Handlers (called from TCP thread)
    def on_file_start(self, msg):
        """Handle file start message"""
        filename = msg.get('filename')
        filesize = msg.get('filesize')
        # Emit signal to handle in main thread (for thread safety if needed, 
        # though FileReceiver writes to disk, UI updates might be needed later)
        self.file_start_signal.emit(filename, filesize)

    def on_file_chunk(self, msg):
        """Handle file chunk message"""
        chunk_id = msg.get('chunk_id')
        data = msg.get('data')
        self.file_chunk_signal.emit(chunk_id, data)

    def on_file_end(self, msg):
        """Handle file end message"""
        checksum = msg.get('checksum')
        self.file_end_signal.emit(checksum)

    # UI/Main Thread File Handlers
    def _handle_file_start_ui(self, filename, filesize):
        """Handle file start in main thread"""
        if self.file_receiver:
            self.file_receiver.start_receiving(filename, filesize)
            if self.meeting_screen:
                self.meeting_screen.add_chat_message("System", f"Receiving file: {filename} ({filesize} bytes)...")

    def _handle_file_chunk_ui(self, chunk_id, data_b64):
        """Handle file chunk in main thread"""
        if self.file_receiver:
            self.file_receiver.receive_chunk(chunk_id, data_b64)

    def _handle_file_end_ui(self, checksum):
        """Handle file end in main thread"""
        if self.file_receiver:
            self.file_receiver.finish_receiving(checksum)
            if self.meeting_screen:
                self.meeting_screen.add_chat_message("System", "File received successfully!")

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Real-Time Communication Client')
    parser.add_argument('--server', default='127.0.0.1', help='Server address (default: 127.0.0.1)')
    parser.add_argument('--tcp-port', type=int, default=5000, help='Server TCP port (default: 5000)')
    parser.add_argument('--udp-port', type=int, default=5001, help='Server UDP port (default: 5001)')
    parser.add_argument('--camera', type=int, help='Camera index (e.g., 0 for laptop, 1 for iVCam)')
    parser.add_argument('--drop-rate', type=float, default=0.0, help='Simulated packet loss rate 0-100 (default: 0)')
    
    args = parser.parse_args()
    
    # Set camera index if provided via command line
    if args.camera is not None:
        os.environ['CAMERA_INDEX'] = str(args.camera)
        print(f"[Main] Camera index set to: {args.camera}")
    
    app = QApplication(sys.argv)
    client = ClientApplication(
        server_host=args.server,
        server_tcp_port=args.tcp_port,
        server_udp_port=args.udp_port,
        simulated_loss_rate=args.drop_rate
    )
    client.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
