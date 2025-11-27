"""
UI Home - Home screen with Start/Join options
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QLineEdit, QMessageBox)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

class HomeScreen(QWidget):
    """Home screen UI"""
    
    # Signals
    start_meeting_signal = pyqtSignal(str, bool, bool)  # name, camera_enabled, mic_enabled
    join_meeting_signal = pyqtSignal(str, str, bool, bool)  # meeting_code, name, camera_enabled, mic_enabled
    
    def __init__(self):
        super().__init__()
        self.camera_enabled = True
        self.mic_enabled = True
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the home screen UI"""
        self.setWindowTitle("Real-Time Communication")
        self.setGeometry(100, 100, 600, 400)
        
        layout = QVBoxLayout()
        layout.setSpacing(20)
        
        # Title
        title = QLabel("Multi-Client Video Conference")
        title.setFont(QFont('Arial', 24, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        layout.addStretch()
        
        # Name input
        name_layout = QHBoxLayout()
        name_label = QLabel("Your Name:")
        name_label.setFont(QFont('Arial', 12))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter your name")
        self.name_input.setFont(QFont('Arial', 12))
        self.name_input.setMinimumHeight(40)
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.name_input)
        layout.addLayout(name_layout)
        
        # Camera and Mic toggles
        controls_layout = QHBoxLayout()
        
        self.camera_btn = QPushButton("📷 Camera ON")
        self.camera_btn.setCheckable(True)
        self.camera_btn.setChecked(True)
        self.camera_btn.setFont(QFont('Arial', 11))
        self.camera_btn.setMinimumHeight(40)
        self.camera_btn.setStyleSheet("""
            QPushButton {
                background-color: #34a853;
                color: white;
                border-radius: 5px;
            }
            QPushButton:checked {
                background-color: #ea4335;
            }
            QPushButton:hover {
                opacity: 0.9;
            }
        """)
        self.camera_btn.clicked.connect(self.toggle_camera)
        
        self.mic_btn = QPushButton("🎤 Mic ON")
        self.mic_btn.setCheckable(True)
        self.mic_btn.setChecked(True)
        self.mic_btn.setFont(QFont('Arial', 11))
        self.mic_btn.setMinimumHeight(40)
        self.mic_btn.setStyleSheet("""
            QPushButton {
                background-color: #34a853;
                color: white;
                border-radius: 5px;
            }
            QPushButton:checked {
                background-color: #ea4335;
            }
            QPushButton:hover {
                opacity: 0.9;
            }
        """)
        self.mic_btn.clicked.connect(self.toggle_mic)
        
        controls_layout.addWidget(self.camera_btn)
        controls_layout.addWidget(self.mic_btn)
        layout.addLayout(controls_layout)
        
        # Start meeting button
        self.start_btn = QPushButton("Start Meeting")
        self.start_btn.setFont(QFont('Arial', 14))
        self.start_btn.setMinimumHeight(60)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #4285f4;
                color: white;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3367d6;
            }
        """)
        self.start_btn.clicked.connect(self.on_start_meeting)
        layout.addWidget(self.start_btn)
        
        # Divider
        divider_layout = QHBoxLayout()
        divider_layout.addWidget(QLabel("─" * 30))
        divider_layout.addWidget(QLabel("OR"))
        divider_layout.addWidget(QLabel("─" * 30))
        layout.addLayout(divider_layout)
        
        # Meeting code input
        code_layout = QHBoxLayout()
        code_label = QLabel("Meeting Code:")
        code_label.setFont(QFont('Arial', 12))
        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("Enter 6-digit code")
        self.code_input.setFont(QFont('Arial', 12))
        self.code_input.setMinimumHeight(40)
        self.code_input.setMaxLength(6)
        code_layout.addWidget(code_label)
        code_layout.addWidget(self.code_input)
        layout.addLayout(code_layout)
        
        # Join meeting button
        self.join_btn = QPushButton("Join Meeting")
        self.join_btn.setFont(QFont('Arial', 14))
        self.join_btn.setMinimumHeight(60)
        self.join_btn.setStyleSheet("""
            QPushButton {
                background-color: #34a853;
                color: white;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2d9348;
            }
        """)
        self.join_btn.clicked.connect(self.on_join_meeting)
        layout.addWidget(self.join_btn)
        
        layout.addStretch()
        
        self.setLayout(layout)
    
    def toggle_camera(self):
        """Toggle camera on/off"""
        self.camera_enabled = not self.camera_btn.isChecked()
        if self.camera_enabled:
            self.camera_btn.setText("📷 Camera ON")
        else:
            self.camera_btn.setText("📷 Camera OFF")
    
    def toggle_mic(self):
        """Toggle mic on/off"""
        self.mic_enabled = not self.mic_btn.isChecked()
        if self.mic_enabled:
            self.mic_btn.setText("🎤 Mic ON")
        else:
            self.mic_btn.setText("🎤 Mic OFF")
    
    def on_start_meeting(self):
        """Handle start meeting button click"""
        name = self.name_input.text().strip()
        
        if not name:
            QMessageBox.warning(self, "Error", "Please enter your name")
            return
        
        self.start_meeting_signal.emit(name, self.camera_enabled, self.mic_enabled)
    
    def on_join_meeting(self):
        """Handle join meeting button click"""
        name = self.name_input.text().strip()
        code = self.code_input.text().strip()
        
        if not name:
            QMessageBox.warning(self, "Error", "Please enter your name")
            return
        
        if not code or len(code) != 6:
            QMessageBox.warning(self, "Error", "Please enter a valid 6-digit meeting code")
            return
        
        self.join_meeting_signal.emit(code, name, self.camera_enabled, self.mic_enabled)
