"""
UI Meeting - Main meeting screen with Google Meet-like layout
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QTextEdit, QLineEdit, QListWidget, 
                             QSplitter, QFileDialog, QScrollArea, QGridLayout,
                             QTabWidget, QComboBox, QFrame)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QSize
from PyQt5.QtGui import QFont, QImage, QPixmap, QIcon
from styles import Theme
import cv2
import numpy as np

class VideoWidget(QLabel):
    """Widget to display a single video stream"""
    
    def __init__(self, participant_name=""):
        super().__init__()
        self.participant_name = participant_name
        self.setMinimumSize(320, 240)
        self.setStyleSheet(f"""
            QLabel {{
                background-color: #000000;
                color: white; /* Ensure text is visible */
                border: 2px solid {Theme.SURFACE_HOVER};
                border-radius: 8px;
            }}
        """)
        self.setAlignment(Qt.AlignCenter)
        self.setText(f"{participant_name}\n(No Video)")
        self.setFont(QFont('Segoe UI', 14))
    
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
            
            # Scale properly maintaining aspect ratio
            scaled_pixmap = pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            
            # Clear text and set pixmap
            self.setText("")  # Clear the "(No Video)" text
            self.setPixmap(scaled_pixmap)
            
        except Exception as e:
            print(f"[VideoWidget] Error updating frame: {e}")

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
        if hasattr(self, 'code_label'):
            self.code_label.setText(f"Code: {meeting_code}")
    
    def setup_ui(self):
        """Setup the meeting screen UI"""
        self.setWindowTitle("Meeting")
        self.setGeometry(50, 50, 1400, 900)
        self.setAttribute(Qt.WA_StyledBackground, True) # Force background paint
        self.setStyleSheet(f"background-color: {Theme.BACKGROUND}; font-family: 'Segoe UI', sans-serif;")
        
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # --- LEFT SIDE: Video Conference Area ---
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(20, 20, 20, 20)
        
        # 1. Header (Ping & Info)
        header_layout = QHBoxLayout()
        
        # Live Indicator
        live_badge = QLabel(" ● LIVE ")
        live_badge.setStyleSheet(f"color: white; background-color: {Theme.ERROR}; border-radius: 4px; font-weight: bold; padding: 2px;")
        header_layout.addWidget(live_badge)
        
        # Ping
        self.ping_label = QLabel("Ping: -- ms")
        self.ping_label.setFont(QFont('Segoe UI', 10, QFont.Bold))
        self.ping_label.setStyleSheet(f"color: {Theme.SUCCESS}; margin-left: 10px;")
        header_layout.addWidget(self.ping_label)
        
        header_layout.addStretch()
        
        # Quality Label (Persistent)
        self.quality_label = QLabel("Quality: 360p")
        self.quality_label.setFont(QFont('Segoe UI', 12, QFont.Bold))
        self.quality_label.setStyleSheet(f"color: {Theme.PRIMARY}; margin-right: 20px;")
        header_layout.addWidget(self.quality_label)
        
        # Meeting Code (Top Right)
        self.code_label = QLabel("Code: ----")
        self.code_label.setStyleSheet(f"color: {Theme.TEXT_MED}; font-family: monospace; font-size: 14px; background-color: {Theme.SURFACE}; padding: 5px 10px; border-radius: 5px;")
        header_layout.addWidget(self.code_label)
        
        left_layout.addLayout(header_layout)
        
        # Notification Toast (Overlay - Top Right of Video Area)
        # We will add this to the left_widget directly so it can float over
        self.notification_label = QLabel(left_widget)
        self.notification_label.setVisible(False)
        self.notification_label.setStyleSheet(f"""
            QLabel {{
                background-color: {Theme.PRIMARY};
                color: black;
                font-weight: bold;
                font-size: 14px;
                padding: 10px 20px;
                border-radius: 20px;
            }}
        """)
        # We will position it dynamically in show_notification
        
        # 2. Video Grid
        self.video_scroll = QScrollArea()
        self.video_scroll.setStyleSheet("background-color: transparent; border: none;")
        self.video_container = QWidget()
        self.video_container.setStyleSheet("background-color: transparent;")
        self.video_grid = QGridLayout()
        self.video_container.setLayout(self.video_grid)
        self.video_scroll.setWidget(self.video_container)
        self.video_scroll.setWidgetResizable(True)
        left_layout.addWidget(self.video_scroll)
        
        # 3. Floating Control Bar
        controls_container = QFrame()
        controls_container.setStyleSheet(f"""
            QFrame {{
                background-color: {Theme.SURFACE};
                border-radius: 30px;
                border: 1px solid {Theme.DIVIDER};
            }}
        """)
        controls_container.setFixedHeight(80)
        controls_layout = QHBoxLayout()
        controls_layout.setAlignment(Qt.AlignCenter)
        controls_layout.setSpacing(15)
        
        # Mic Button
        self.mic_btn = QPushButton("🎤")
        self.mic_btn.setFixedSize(60, 60)
        self.mic_btn.setCheckable(True)
        self.mic_btn.setChecked(True)
        self.mic_btn.setCursor(Qt.PointingHandCursor)
        self.mic_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Theme.SURFACE_HOVER};
                border-radius: 30px;
                font-size: 24px;
            }}
            QPushButton:checked {{
                background-color: {Theme.SURFACE_HOVER}; /* Default styling for ON */
                border: 2px solid {Theme.SUCCESS};
            }}
            QPushButton:!checked {{
                background-color: {Theme.ERROR};
                border: 2px solid {Theme.ERROR};
            }}
        """)
        self.mic_btn.clicked.connect(self.on_toggle_mic)
        
        # Camera Button
        self.camera_btn = QPushButton("📹")
        self.camera_btn.setFixedSize(60, 60)
        self.camera_btn.setCheckable(True)
        self.camera_btn.setChecked(True)
        self.camera_btn.setCursor(Qt.PointingHandCursor)
        self.camera_btn.setStyleSheet(self.mic_btn.styleSheet()) # Reuse same style logic
        self.camera_btn.clicked.connect(self.on_toggle_camera)
        
        # Stats Button
        self.stats_btn = QPushButton("📊")
        self.stats_btn.setFixedSize(50, 50)
        self.stats_btn.setCursor(Qt.PointingHandCursor)
        self.stats_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Theme.SURFACE_HOVER};
                border-radius: 25px;
                font-size: 20px;
            }}
             QPushButton:hover {{
                background-color: {Theme.PRIMARY};
            }}
        """)
        self.stats_btn.clicked.connect(self.show_stats_signal.emit)
        
        # Leave Button
        self.leave_btn = QPushButton("❌")
        self.leave_btn.setFixedSize(60, 60)
        self.leave_btn.setCursor(Qt.PointingHandCursor)
        self.leave_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Theme.ERROR};
                border-radius: 30px;
                font-size: 24px;
            }}
            QPushButton:hover {{
                background-color: #B00020;
            }}
        """)
        self.leave_btn.clicked.connect(self.leave_meeting_signal.emit)
        
        controls_layout.addWidget(self.mic_btn)
        controls_layout.addWidget(self.camera_btn)
        controls_layout.addSpacing(20)
        controls_layout.addWidget(self.stats_btn)
        controls_layout.addSpacing(40)
        controls_layout.addWidget(self.leave_btn)
        
        controls_container.setLayout(controls_layout)
        
        # Center the controls
        bottom_box = QHBoxLayout()
        bottom_box.addStretch()
        bottom_box.addWidget(controls_container)
        bottom_box.addStretch()
        
        left_layout.addLayout(bottom_box)
        left_widget.setLayout(left_layout)
        
        # --- RIGHT SIDE: Sidebar (Chat & Participants) ---
        right_widget = QWidget()
        right_widget.setFixedWidth(350)
        right_widget.setStyleSheet(f"background-color: {Theme.SURFACE}; border-left: 1px solid {Theme.DIVIDER};")
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(15, 15, 15, 15)
        
        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(Theme.TAB_WIDGET)
        
        # -- Chat Tab --
        chat_widget = QWidget()
        chat_layout = QVBoxLayout()
        
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setFont(QFont('Segoe UI', 10))
        self.chat_display.setStyleSheet(f"background-color: {Theme.BACKGROUND}; border: 1px solid {Theme.DIVIDER}; border-radius: 8px; padding: 10px;")
        chat_layout.addWidget(self.chat_display)
        
        # Target Combo
        target_layout = QHBoxLayout()
        target_label = QLabel("To:")
        target_label.setStyleSheet(f"color: {Theme.TEXT_MED};")
        self.chat_target_combo = QComboBox()
        self.chat_target_combo.addItem("Everyone")
        self.chat_target_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {Theme.BACKGROUND};
                color: {Theme.TEXT_HIGH};
                border: 1px solid {Theme.DIVIDER};
                padding: 5px;
                border-radius: 5px;
            }}
        """)
        target_layout.addWidget(target_label)
        target_layout.addWidget(self.chat_target_combo)
        chat_layout.addLayout(target_layout)
        
        # Input Area
        input_row = QHBoxLayout()
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Type a message...")
        self.chat_input.setStyleSheet(Theme.INPUT)
        self.chat_input.returnPressed.connect(self.on_send_chat)
        
        self.send_btn = QPushButton("➤")
        self.send_btn.setFixedSize(40, 40)
        self.send_btn.setCursor(Qt.PointingHandCursor)
        self.send_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Theme.PRIMARY};
                color: black;
                border-radius: 20px;
                font-weight: bold;
            }}
             QPushButton:hover {{
                background-color: {Theme.PRIMARY_VARIANT};
            }}
        """)
        self.send_btn.clicked.connect(self.on_send_chat)
        
        input_row.addWidget(self.chat_input)
        input_row.addWidget(self.send_btn)
        chat_layout.addLayout(input_row)
        
        # File Send Button
        self.file_btn = QPushButton("📎 Send File")
        self.file_btn.setCursor(Qt.PointingHandCursor)
        self.file_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: 1px solid {Theme.DIVIDER};
                color: {Theme.TEXT_MED};
                border-radius: 5px;
                padding: 8px;
            }}
            QPushButton:hover {{
                background-color: {Theme.SURFACE_HOVER};
                color: {Theme.TEXT_HIGH};
            }}
        """)
        self.file_btn.clicked.connect(self.on_send_file)
        chat_layout.addWidget(self.file_btn)
        
        chat_widget.setLayout(chat_layout)
        
        # -- Participants Tab --
        part_widget = QWidget()
        part_layout = QVBoxLayout()
        
        self.participants_list = QListWidget()
        self.participants_list.setFont(QFont('Segoe UI', 11))
        self.participants_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {Theme.BACKGROUND};
                border: 1px solid {Theme.DIVIDER};
                border-radius: 8px;
                color: {Theme.TEXT_HIGH};
                padding: 5px;
            }}
            QListWidget::item {{
                padding: 10px;
                border-bottom: 1px solid {Theme.DIVIDER};
            }}
        """)
        part_layout.addWidget(self.participants_list)
        part_widget.setLayout(part_layout)
        
        self.tabs.addTab(chat_widget, "Chats")
        self.tabs.addTab(part_widget, "People")
        
        right_layout.addWidget(self.tabs)
        right_widget.setLayout(right_layout)
        
        # --- SPLITTER ---
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([900, 350])
        splitter.setHandleWidth(2)
        splitter.setStyleSheet(f"QSplitter::handle {{ background-color: {Theme.DIVIDER}; }}")
        
        main_layout.addWidget(splitter)
        self.setLayout(main_layout)
        
    def add_video_stream(self, participant_id, participant_name):
        """Add a video stream widget"""
        if participant_id not in self.video_widgets:
            widget = VideoWidget(participant_name)
            self.video_widgets[participant_id] = widget
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
            item = self.video_grid.itemAt(i)
            if item.widget():
                item.widget().setParent(None)
        
        count = len(self.video_widgets)
        if count == 0:
            return
        
        cols = int(np.ceil(np.sqrt(count)))
        rows = int(np.ceil(count / cols))
        
        for idx, (participant_id, widget) in enumerate(self.video_widgets.items()):
            row = idx // cols
            col = idx % cols
            widget.show()
            self.video_grid.addWidget(widget, row, col)
    
    def update_video_frame(self, participant_id, frame):
        """Update video frame for a participant"""
        if participant_id in self.video_widgets:
            self.video_widgets[participant_id].update_frame(frame)
    
    def clear_video_frame(self, participant_id):
        """Clear video frame (show placeholder)"""
        if participant_id in self.video_widgets:
            widget = self.video_widgets[participant_id]
            widget.clear()
            widget.setText(f"{widget.participant_name}\n(No Video)")
    
    def show_no_video(self, participant_id, participant_name=None):
        """Show 'No Video' placeholder"""
        if participant_id in self.video_widgets:
            widget = self.video_widgets[participant_id]
            name = participant_name or widget.participant_name
            widget.clear()
            widget.setText(f"{name}\n(No Video)")
            
    def request_frame_update(self):
        pass
    
    def add_chat_message(self, sender, message, is_private=False):
        """Add a message to chat"""
        color = Theme.PRIMARY if sender == self.client_name else Theme.SECONDARY
        if is_private:
             self.chat_display.append(f"<div style='margin-bottom: 5px;'><span style='color:#FF5252; font-weight:bold;'>(Private) {sender}</span>: <span style='color:{Theme.TEXT_MED};'>{message}</span></div>")
        else:
            self.chat_display.append(f"<div style='margin-bottom: 5px;'><span style='color:{color}; font-weight:bold;'>{sender}</span>: <span style='color:{Theme.TEXT_HIGH};'>{message}</span></div>")
    
    def on_send_chat(self):
        """Send chat message"""
        message = self.chat_input.text().strip()
        target = self.chat_target_combo.currentText()
        if message:
            self.send_chat_signal.emit(message + "|||" + target)
            self.chat_input.clear()

    def update_chat_participants(self, participants):
        """Update the combo box with list of participants"""
        current = self.chat_target_combo.currentText()
        self.chat_target_combo.clear()
        self.chat_target_combo.addItem("Everyone")
        for p in participants:
            self.chat_target_combo.addItem(p)
        
        index = self.chat_target_combo.findText(current)
        if index >= 0:
            self.chat_target_combo.setCurrentIndex(index)
    
    def on_send_file(self):
        """Open file dialog and send file"""
        filepath, _ = QFileDialog.getOpenFileName(self, "Select File to Send")
        if filepath:
            target = self.chat_target_combo.currentText()
            self.send_file_signal.emit(filepath, target)
            self.add_chat_message("System", f"Sending file: {os.path.basename(filepath)}")
    
    def on_toggle_mic(self):
        """Toggle microphone"""
        self.mic_enabled = self.mic_btn.isChecked()
        self.toggle_mic_signal.emit(self.mic_enabled)
    
    def on_toggle_camera(self):
        """Toggle camera"""
        self.camera_enabled = self.camera_btn.isChecked()
        self.toggle_camera_signal.emit(self.camera_enabled)
    
    def set_mic_state(self, enabled):
        self.mic_enabled = enabled
        self.mic_btn.setChecked(enabled)
    
    def set_camera_state(self, enabled):
        self.camera_enabled = enabled
        self.camera_btn.setChecked(enabled)

    def add_participant_to_list(self, name, is_host=False):
        """Add participant to the list"""
        display_name = f"{name} (Host)" if is_host else name
        items = self.participants_list.findItems(display_name, Qt.MatchExactly)
        if not items:
            self.participants_list.addItem(display_name)
            self._update_chat_combo()
    
    def remove_participant_from_list(self, name):
        """Remove participant from the list"""
        for item in self.participants_list.findItems(name, Qt.MatchStartsWith):
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
            clean_name = item_text.replace(" (Host)", "")
            if clean_name != self.client_name:
                self.chat_target_combo.addItem(clean_name)
        
        index = self.chat_target_combo.findText(current)
        if index >= 0:
            self.chat_target_combo.setCurrentIndex(index)
        
    def show_meeting_info(self):
        pass # Removed default dialog, replaced with inline code display
        
    def update_ping(self, rtt_ms):
        """Update the ping/RTT label with color coding"""
        self.ping_label.setText(f"Ping: {int(rtt_ms)} ms")
        
        if rtt_ms < 100:
            color = Theme.SUCCESS
        elif rtt_ms < 300:
            color = "#FFC107"
        else:
            color = Theme.ERROR
            
        self.ping_label.setStyleSheet(f"color: {color}; margin-left: 10px; font-weight: bold;")
            
    def update_quality_display(self, quality_text):
        """Update the quality label and show notification"""
        # Update persistent label
        self.quality_label.setText(f"Quality: {quality_text}")
        
        # Show toast notification
        self.show_notification(f"Quality changed to {quality_text} ⚡")

    def show_notification(self, message):
        """Show a temporary floating notification"""
        self.notification_label.setText(message)
        self.notification_label.adjustSize()
        
        # Position: Top Right relative to the container, with some margin
        # We use parent's geometry
        parent_width = self.notification_label.parent().width()
        
        x = parent_width - self.notification_label.width() - 30
        y = 70 # Below header
        
        self.notification_label.move(x, y)
        self.notification_label.raise_()
        self.notification_label.show()
        
        # Hide after 3 seconds
        QTimer.singleShot(3000, self.notification_label.hide)
