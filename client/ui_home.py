"""
UI Home - Home screen with Start/Join options
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QLineEdit, QMessageBox, QFrame, QGraphicsDropShadowEffect)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QColor
from styles import Theme

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
        self.setGeometry(100, 100, 1280, 900)  # Drastically Increased Size
        self.setAttribute(Qt.WA_StyledBackground, True) # Force background paint
        # Apply background directly to self to ensure it catches
        self.setStyleSheet(f"background-color: {Theme.BACKGROUND}; font-family: 'Segoe UI', sans-serif;")
        
        # Main Layout
        main_layout = QVBoxLayout()
        main_layout.setAlignment(Qt.AlignCenter)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # --- Center Card ---
        card = QFrame()
        card.setFixedSize(700, 800) # Drastically Increased Card Size
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {Theme.SURFACE};
                border-radius: 20px;
                border: 1px solid {Theme.DIVIDER};
            }}
        """)
        
        # Shadow for card
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(40)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 10)
        card.setGraphicsEffect(shadow)
        
        card_layout = QVBoxLayout()
        card_layout.setSpacing(25) # More breathing room
        card_layout.setContentsMargins(50, 50, 50, 50)
        
        # Logo/Icon Placeholder
        logo = QLabel("⚡")
        logo.setAlignment(Qt.AlignCenter)
        logo.setFont(QFont('Segoe UI Emoji', 72))
        logo.setStyleSheet("background-color: transparent; border: none;")
        card_layout.addWidget(logo)
        
        # Title
        title = QLabel("Connect")
        title.setFont(QFont('Segoe UI', 32, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"color: {Theme.TEXT_HIGH}; border: none;")
        card_layout.addWidget(title)
        
        # Subtitle
        subtitle = QLabel("Start or join a video meeting")
        subtitle.setFont(QFont('Segoe UI', 16))
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet(f"color: {Theme.TEXT_MED}; border: none; margin-bottom: 20px;")
        card_layout.addWidget(subtitle)
        
        # Name Input
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter your name")
        self.name_input.setStyleSheet(Theme.INPUT)
        card_layout.addWidget(self.name_input)
        
        # Meeting Code Input
        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("Meeting Code (to Join)")
        self.code_input.setStyleSheet(Theme.INPUT)
        card_layout.addWidget(self.code_input)
        
        # Toggles Row
        toggles_layout = QHBoxLayout()
        toggles_layout.setSpacing(15)
        
        self.mic_btn = QPushButton("🎤 Mic ON")
        self.mic_btn.setCheckable(True)
        self.mic_btn.setChecked(True)
        self.mic_btn.setCursor(Qt.PointingHandCursor)
        self.mic_btn.setStyleSheet(Theme.BTN_TOGGLE)
        self.mic_btn.clicked.connect(self.toggle_mic)
        
        self.camera_btn = QPushButton("📷 Cam ON")
        self.camera_btn.setCheckable(True)
        self.camera_btn.setChecked(True)
        self.camera_btn.setCursor(Qt.PointingHandCursor)
        self.camera_btn.setStyleSheet(Theme.BTN_TOGGLE)
        self.camera_btn.clicked.connect(self.toggle_camera)
        
        toggles_layout.addWidget(self.mic_btn)
        toggles_layout.addWidget(self.camera_btn)
        card_layout.addLayout(toggles_layout)
        
        card_layout.addStretch()
        
        # Buttons
        self.join_btn = QPushButton("Join Meeting")
        self.join_btn.setCursor(Qt.PointingHandCursor)
        self.join_btn.setStyleSheet(Theme.BTN_PRIMARY)
        self.join_btn.clicked.connect(self.on_join_meeting)
        card_layout.addWidget(self.join_btn)
        
        self.start_btn = QPushButton("Create Meeting")
        self.start_btn.setCursor(Qt.PointingHandCursor)
        self.start_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {Theme.PRIMARY};
                font-weight: bold;
                font-size: 18px;
                border: none;
            }}
            QPushButton:hover {{
                color: {Theme.TEXT_HIGH};
            }}
        """)
        self.start_btn.clicked.connect(self.on_start_meeting)
        card_layout.addWidget(self.start_btn)
        
        card.setLayout(card_layout)
        main_layout.addWidget(card)
        self.setLayout(main_layout)
    
    def toggle_camera(self):
        """Toggle camera on/off"""
        # Fix logic: camera_enabled tracks the INTENDED state.
        # Button checked means "ON".
        self.camera_enabled = self.camera_btn.isChecked()
        
        if self.camera_enabled:
            self.camera_btn.setText("📷 Cam ON")
        else:
            self.camera_btn.setText("📷 Cam OFF")
    
    def toggle_mic(self):
        """Toggle mic on/off"""
        self.mic_enabled = self.mic_btn.isChecked()
        
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
        
        # If code is empty, maybe they wanted to start?
        # But we have separate buttons now.
        if not code:
             QMessageBox.warning(self, "Error", "Please enter a meeting code to join")
             return
        
        if len(code) != 6:
            QMessageBox.warning(self, "Error", "Please enter a valid 6-digit meeting code")
            return
        
        self.join_meeting_signal.emit(code, name, self.camera_enabled, self.mic_enabled)
