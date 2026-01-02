"""
UI Meeting - Main meeting screen with Google Meet-like layout
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QTextEdit, QLineEdit, QListWidget, 
                             QSplitter, QFileDialog, QScrollArea, QGridLayout,
                             QTabWidget, QComboBox)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QImage, QPixmap
import cv2
import numpy as np

class VideoWidget(QLabel):
    """Widget to display a single video stream"""
    
    def __init__(self, participant_name=""):
        super().__init__()
        self.participant_name = participant_name
        self.setMinimumSize(320, 240)
        self.setStyleSheet("border: 2px solid #333; background-color: black;")
        self.setAlignment(Qt.AlignCenter)
        self.setText(f"{participant_name}\n(No Video)")
        self.setStyleSheet("color: white; font-size: 14px; background-color: #333;")
    
    def update_frame(self, frame):
        """Update the video frame"""
        if frame is None:
            return
        
        try:
            # Convert frame to Qt format
            height, width, channel = frame.shape
            bytes_per_line = 3 * width
            q_img = QImage(frame.data, width, height, bytes_per_line, QImage.Format_RGB888)
            q_img = q_img.rgbSwapped()  # BGR to RGB
            
            # Scale to widget size
            pixmap = QPixmap.fromImage(q_img)
            pixmap = pixmap.scaled(self.width(), self.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            
            # Clear text and set pixmap
            self.setText("")  # Clear the "(No Video)" text
            self.setPixmap(pixmap)
            
            # Debug: Log first frame update
            if not hasattr(self, '_first_frame_logged'):
                print(f"[VideoWidget] First frame displayed for {self.participant_name}: {width}x{height}")
                self._first_frame_logged = True
        except Exception as e:
            print(f"[VideoWidget] Error updating frame for {self.participant_name}: {e}")
            import traceback
            traceback.print_exc()

class MeetingScreen(QWidget):
    """Main meeting screen UI"""
    
    # Signals
    send_chat_signal = pyqtSignal(str)  # message
    send_file_signal = pyqtSignal(str, str)  # filepath, target
    toggle_mic_signal = pyqtSignal(bool)  # enabled
    toggle_camera_signal = pyqtSignal(bool)  # enabled
    leave_meeting_signal = pyqtSignal()
    show_stats_signal = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.video_widgets = {}  # {participant_id: VideoWidget}
        self.mic_enabled = True
        self.camera_enabled = True
        self.client_name = ""
        self.meeting_code = ""
        
        self.setup_ui()
        
        # Update timer for video frames
        self.timer = QTimer()
        self.timer.timeout.connect(self.request_frame_update)
        self.timer.start(33)  # ~30 FPS
        
    def set_meeting_info(self, meeting_code, client_name):
        """Set meeting info"""
        self.meeting_code = meeting_code
        self.client_name = client_name
        if hasattr(self, 'top_label'):
            self.top_label.setText(f"Meeting: {meeting_code}")
    
    def setup_ui(self):
        """Setup the meeting screen UI"""
        self.setWindowTitle("Meeting")
        self.setGeometry(50, 50, 1400, 900)
        
        main_layout = QHBoxLayout()
        
        # Left side: Video grid
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        
        # Header with Info Button
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(10, 10, 10, 0)
        
        self.top_label = QLabel("Meeting in Progress")
        self.top_label.setFont(QFont('Arial', 14, QFont.Bold))
        
        info_btn = QPushButton("ℹ️")
        info_btn.setFixedSize(30, 30)
        info_btn.setToolTip("Meeting Information")
        info_btn.clicked.connect(self.show_meeting_info)
        info_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 2px solid white;
                border-radius: 15px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.2);
            }
        """)
        
        # Add to header
        header_layout.addWidget(self.top_label)
        header_layout.addWidget(info_btn)
        header_layout.addStretch()
        left_layout.addLayout(header_layout)
        
        # Video grid container
        self.video_scroll = QScrollArea()
        self.video_container = QWidget()
        self.video_grid = QGridLayout()
        self.video_container.setLayout(self.video_grid)
        self.video_scroll.setWidget(self.video_container)
        self.video_scroll.setWidgetResizable(True)
        left_layout.addWidget(self.video_scroll)
        
        # Control bar at bottom
        controls_layout = QHBoxLayout()
        
        self.mic_btn = QPushButton("🎤 Mic")
        self.mic_btn.setCheckable(True)
        self.mic_btn.setChecked(True)
        self.mic_btn.clicked.connect(self.on_toggle_mic)
        self.mic_btn.setMinimumHeight(50)
        self.mic_btn.setStyleSheet(self._get_control_btn_style())
        
        self.camera_btn = QPushButton("📹 Camera")
        self.camera_btn.setCheckable(True)
        self.camera_btn.setChecked(True)
        self.camera_btn.clicked.connect(self.on_toggle_camera)
        self.camera_btn.setMinimumHeight(50)
        self.camera_btn.setStyleSheet(self._get_control_btn_style())
        
        self.stats_btn = QPushButton("📊 Stats")
        self.stats_btn.clicked.connect(self.show_stats_signal.emit)
        self.stats_btn.setMinimumHeight(50)
        self.stats_btn.setStyleSheet(self._get_control_btn_style())
        
        self.leave_btn = QPushButton("🚪 Leave")
        self.leave_btn.clicked.connect(self.leave_meeting_signal.emit)
        self.leave_btn.setMinimumHeight(50)
        self.leave_btn.setStyleSheet("""
            QPushButton {
                background-color: #ea4335;
                color: white;
                border-radius: 5px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #d33426;
            }
        """)
        
        controls_layout.addWidget(self.mic_btn)
        controls_layout.addWidget(self.camera_btn)
        controls_layout.addWidget(self.stats_btn)
        controls_layout.addStretch()
        controls_layout.addWidget(self.leave_btn)
        
        left_layout.addLayout(controls_layout)
        left_widget.setLayout(left_layout)
        
        # Right side: Chat and file sharing
        right_widget = QWidget()
        right_widget.setMaximumWidth(400)
        right_layout = QVBoxLayout()
        
        # Tab Widget for Chat and Participants
        self.tabs = QTabWidget()
        
        # --- Chat Tab ---
        chat_widget = QWidget()
        chat_layout = QVBoxLayout()
        chat_layout.setContentsMargins(0, 0, 0, 0)
        
        # Target selector
        target_layout = QHBoxLayout()
        target_label = QLabel("To:")
        self.chat_target_combo = QComboBox()
        self.chat_target_combo.addItem("Everyone")
        target_layout.addWidget(target_label)
        target_layout.addWidget(self.chat_target_combo)
        chat_layout.addLayout(target_layout)
        
        # Chat display
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setFont(QFont('Arial', 11))
        chat_layout.addWidget(self.chat_display)
        
        # Chat input
        chat_input_layout = QHBoxLayout()
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Type a message...")
        self.chat_input.setFont(QFont('Arial', 11))
        self.chat_input.returnPressed.connect(self.on_send_chat)
        
        self.send_btn = QPushButton("Send")
        self.send_btn.clicked.connect(self.on_send_chat)
        self.send_btn.setStyleSheet("""
            QPushButton {
                background-color: #4285f4;
                color: white;
                border-radius: 3px;
                padding: 8px 16px;
            }
        """)
        
        chat_input_layout.addWidget(self.chat_input)
        chat_input_layout.addWidget(self.send_btn)
        chat_layout.addLayout(chat_input_layout)
        chat_widget.setLayout(chat_layout)
        
        # --- Participants Tab ---
        participants_widget = QWidget()
        participants_layout = QVBoxLayout()
        participants_layout.setContentsMargins(0, 0, 0, 0)
        
        self.participants_list = QListWidget()
        self.participants_list.setFont(QFont('Arial', 12))
        participants_layout.addWidget(self.participants_list)
        participants_widget.setLayout(participants_layout)
        
        # Add tabs
        self.tabs.addTab(chat_widget, "💬 Chat")
        self.tabs.addTab(participants_widget, "👥 Participants")
        
        right_layout.addWidget(self.tabs)
        
        # File sharing
        file_layout = QHBoxLayout()
        self.file_btn = QPushButton("📎 Send File")
        self.file_btn.clicked.connect(self.on_send_file)
        self.file_btn.setStyleSheet("""
            QPushButton {
                background-color: #34a853;
                color: white;
                border-radius: 3px;
                padding: 8px;
            }
        """)
        file_layout.addWidget(self.file_btn)
        right_layout.addLayout(file_layout)
        
        right_widget.setLayout(right_layout)
        
        # Add to main splitter
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        
        main_layout.addWidget(splitter)
        self.setLayout(main_layout)
    
    def _get_control_btn_style(self):
        """Get control button stylesheet"""
        return """
            QPushButton {
                background-color: #333;
                color: white;
                border-radius: 5px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #555;
            }
            QPushButton:checked {
                background-color: #4285f4;
            }
        """
    
    def add_video_stream(self, participant_id, participant_name):
        """Add a video stream widget"""
        if participant_id not in self.video_widgets:
            widget = VideoWidget(participant_name)
            self.video_widgets[participant_id] = widget
            print(f"[MeetingScreen] Added widget for {participant_id}, visible={self.isVisible()}, window visible={self.window().isVisible()}")
            
            # Arrange in grid
            self._rearrange_video_grid()
    
    def remove_video_stream(self, participant_id):
        """Remove a video stream widget"""
        if participant_id in self.video_widgets:
            widget = self.video_widgets[participant_id]
            self.video_grid.removeWidget(widget)
            widget.deleteLater()
            del self.video_widgets[participant_id]
            
            self._rearrange_video_grid()
    
    def _rearrange_video_grid(self):
        """Rearrange video widgets in grid"""
        # Clear current layout
        for i in reversed(range(self.video_grid.count())):
            self.video_grid.itemAt(i).widget().setParent(None)
        
        # Calculate grid dimensions
        count = len(self.video_widgets)
        if count == 0:
            return
        
        cols = int(np.ceil(np.sqrt(count)))
        rows = int(np.ceil(count / cols))
        
        print(f"[MeetingScreen] Rearranging {count} videos in {rows}x{cols} grid")
        
        # Add widgets to grid
        for idx, (participant_id, widget) in enumerate(self.video_widgets.items()):
            row = idx // cols
            col = idx % cols
            print(f"[MeetingScreen] Placing {participant_id} at ({row}, {col})")
            widget.show()  # Explicitly show the widget
            self.video_grid.addWidget(widget, row, col)
        
        # Force layout update
        self.video_grid.update()
        self.video_container.updateGeometry()
        self.video_scroll.updateGeometry()
        self.update()  # Force repaint
    
    def update_video_frame(self, participant_id, frame):
        """Update video frame for a participant"""
        if participant_id in self.video_widgets:
            self.video_widgets[participant_id].update_frame(frame)
    
    def clear_video_frame(self, participant_id):
        """Clear video frame for a participant (show placeholder)"""
        if participant_id in self.video_widgets:
            widget = self.video_widgets[participant_id]
            widget.clear()
            widget.setText(f"{widget.participant_name}\n(No Video)")
    
    def show_no_video(self, participant_id, participant_name=None):
        """Show 'No Video' placeholder for a participant when camera is off"""
        if participant_id in self.video_widgets:
            widget = self.video_widgets[participant_id]
            name = participant_name or widget.participant_name
            widget.clear()  # Clear any existing pixmap
            widget.setText(f"{name}\n(No Video)")
            widget.setStyleSheet("color: white; font-size: 14px; background-color: #333; border: 2px solid #333;")
            print(f"[MeetingScreen] Showing 'No Video' for {participant_id}")
    
    def request_frame_update(self):
        """Request frame updates (override in main app)"""
        pass
    
    def add_chat_message(self, sender, message, is_private=False):
        """Add a message to chat"""
        if is_private:
             self.chat_display.append(f"<span style='color:red; font-style:italic'>(Privately) <b>{sender}:</b> {message}</span>")
        else:
            self.chat_display.append(f"<b>{sender}:</b> {message}")
    
    def on_send_chat(self):
        """Send chat message"""
        message = self.chat_input.text().strip()
        target = self.chat_target_combo.currentText()
        if message:
            # Emit message AND target
            self.send_chat_signal.emit(message + "|||" + target) # Hacky split for now or change signal
            self.chat_input.clear()

    def update_chat_participants(self, participants):
        """Update the combo box with list of participants"""
        current = self.chat_target_combo.currentText()
        self.chat_target_combo.clear()
        self.chat_target_combo.addItem("Everyone")
        for p in participants:
            self.chat_target_combo.addItem(p)
        
        # Restore selection if still exists
        index = self.chat_target_combo.findText(current)
        if index >= 0:
            self.chat_target_combo.setCurrentIndex(index)
    
    def on_send_file(self):
        """Open file dialog and send file"""
        filepath, _ = QFileDialog.getOpenFileName(self, "Select File to Send")
        if filepath:
            target = self.chat_target_combo.currentText()
            self.send_file_signal.emit(filepath, target)
            
            if target == "Everyone":
                self.add_chat_message("System", f"Sending file: {os.path.basename(filepath)}")
            else:
                self.add_chat_message("System", f"Sending file to {target}: {os.path.basename(filepath)}", is_private=True)
    
    def on_toggle_mic(self):
        """Toggle microphone"""
        self.mic_enabled = self.mic_btn.isChecked()
        self.toggle_mic_signal.emit(self.mic_enabled)
        
        if self.mic_enabled:
            self.mic_btn.setText("🎤 Mic")
        else:
            self.mic_btn.setText("🎤 Mic (Off)")
    
    def on_toggle_camera(self):
        """Toggle camera"""
        print(f"[MeetingScreen] ===== Camera button clicked! =====")
        self.camera_enabled = self.camera_btn.isChecked()
        print(f"[MeetingScreen] camera_enabled = {self.camera_enabled}")
        print(f"[MeetingScreen] Emitting toggle_camera_signal with: {self.camera_enabled}")
        self.toggle_camera_signal.emit(self.camera_enabled)
        print(f"[MeetingScreen] Signal emitted successfully")
        
        if self.camera_enabled:
            self.camera_btn.setText("📹 Camera")
        else:
            self.camera_btn.setText("📹 Camera (Off)")
        
        print(f"[MeetingScreen] Button text updated, camera toggle complete")
    
    def set_mic_state(self, enabled):
        """Set initial mic state"""
        self.mic_enabled = enabled
        self.mic_btn.setChecked(enabled)
        if enabled:
            self.mic_btn.setText("🎤 Mic")
        else:
            self.mic_btn.setText("🎤 Mic (Off)")
    
    def set_camera_state(self, enabled):
        """Set initial camera state"""
        self.camera_enabled = enabled
        self.camera_btn.setChecked(enabled)
        if enabled:
            self.camera_btn.setText("📹 Camera")
        else:
            self.camera_btn.setText("📹 Camera (Off)")

    def add_participant_to_list(self, name, is_host=False):
        """Add participant to the list"""
        display_name = f"{name} (Host)" if is_host else name
        
        # Check if already exists to avoid duplicates
        items = self.participants_list.findItems(display_name, Qt.MatchExactly)
        if not items:
            self.participants_list.addItem(display_name)
            self._update_chat_combo()
    
    def remove_participant_from_list(self, name):
        """Remove participant from the list"""
        # Try both with and without host label
        for item in self.participants_list.findItems(name, Qt.MatchStartsWith):
            # Check exact match or match with host label
            if item.text() == name or item.text() == f"{name} (Host)":
                row = self.participants_list.row(item)
                self.participants_list.takeItem(row)
                self._update_chat_combo()
                break

    def _update_chat_combo(self):
        """Update the combo box from participant list"""
        current = self.chat_target_combo.currentText()
        self.chat_target_combo.clear()
        self.chat_target_combo.addItem("Everyone")
        
        for i in range(self.participants_list.count()):
            item_text = self.participants_list.item(i).text()
            # Strip (Host) if present
            clean_name = item_text.replace(" (Host)", "")
            
            # Don't add self to target list
            if clean_name != self.client_name:
                self.chat_target_combo.addItem(clean_name)
        
        # Restore selection if still exists
        index = self.chat_target_combo.findText(current)
        if index >= 0:
            self.chat_target_combo.setCurrentIndex(index)
            
    def show_meeting_info(self):
        """Show meeting info dialog"""
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.information(
            self, 
            "Meeting Information", 
            f"Meeting Details\n\nCode: {self.meeting_code}\nUser: {self.client_name}"
        )
