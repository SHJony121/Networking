"""
UI Meeting - Main meeting screen with Google Meet-like layout
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QTextEdit, QLineEdit, QListWidget, 
                             QSplitter, QFileDialog, QScrollArea, QGridLayout)
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
    send_file_signal = pyqtSignal(str)  # filepath
    toggle_mic_signal = pyqtSignal(bool)  # enabled
    toggle_camera_signal = pyqtSignal(bool)  # enabled
    leave_meeting_signal = pyqtSignal()
    show_stats_signal = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.video_widgets = {}  # {participant_id: VideoWidget}
        self.mic_enabled = True
        self.camera_enabled = True
        self.setup_ui()
        
        # Update timer for video frames
        self.timer = QTimer()
        self.timer.timeout.connect(self.request_frame_update)
        self.timer.start(33)  # ~30 FPS
    
    def setup_ui(self):
        """Setup the meeting screen UI"""
        self.setWindowTitle("Meeting")
        self.setGeometry(50, 50, 1400, 900)
        
        main_layout = QHBoxLayout()
        
        # Left side: Video grid
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        
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
        
        # Tabs-like header
        tabs_layout = QHBoxLayout()
        chat_tab = QLabel("💬 Chat")
        chat_tab.setFont(QFont('Arial', 14, QFont.Bold))
        tabs_layout.addWidget(chat_tab)
        tabs_layout.addStretch()
        right_layout.addLayout(tabs_layout)
        
        # Chat display
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setFont(QFont('Arial', 11))
        right_layout.addWidget(self.chat_display)
        
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
        right_layout.addLayout(chat_input_layout)
        
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
    
    def request_frame_update(self):
        """Request frame updates (override in main app)"""
        pass
    
    def add_chat_message(self, sender, message):
        """Add a message to chat"""
        self.chat_display.append(f"<b>{sender}:</b> {message}")
    
    def on_send_chat(self):
        """Send chat message"""
        message = self.chat_input.text().strip()
        if message:
            self.send_chat_signal.emit(message)
            self.chat_input.clear()
    
    def on_send_file(self):
        """Open file dialog and send file"""
        filepath, _ = QFileDialog.getOpenFileName(self, "Select File to Send")
        if filepath:
            self.send_file_signal.emit(filepath)
            self.add_chat_message("System", f"Sending file: {os.path.basename(filepath)}")
    
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
        self.camera_enabled = self.camera_btn.isChecked()
        self.toggle_camera_signal.emit(self.camera_enabled)
        
        if self.camera_enabled:
            self.camera_btn.setText("📹 Camera")
        else:
            self.camera_btn.setText("📹 Camera (Off)")
    
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
