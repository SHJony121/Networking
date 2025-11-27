"""
UI Waiting Room - Host waiting room to approve participants
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QListWidget, QListWidgetItem, QMessageBox)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont

class WaitingRoomScreen(QWidget):
    """Waiting room screen for host"""
    
    # Signals
    allow_participant_signal = pyqtSignal(str)  # participant_name
    deny_participant_signal = pyqtSignal(str)  # participant_name
    start_meeting_signal = pyqtSignal()
    
    def __init__(self, meeting_code):
        super().__init__()
        self.meeting_code = meeting_code
        self.pending_participants = []  # List of participant names
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the waiting room UI"""
        self.setWindowTitle("Waiting Room")
        self.setGeometry(100, 100, 600, 500)
        
        layout = QVBoxLayout()
        layout.setSpacing(20)
        
        # Title
        title = QLabel("Waiting Room")
        title.setFont(QFont('Arial', 20, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Meeting code display
        code_layout = QHBoxLayout()
        code_label = QLabel("Meeting Code:")
        code_label.setFont(QFont('Arial', 14))
        self.code_display = QLabel(self.meeting_code)
        self.code_display.setFont(QFont('Arial', 24, QFont.Bold))
        self.code_display.setStyleSheet("color: #4285f4;")
        code_layout.addWidget(code_label)
        code_layout.addWidget(self.code_display)
        code_layout.addStretch()
        layout.addLayout(code_layout)
        
        # Instructions
        instructions = QLabel("Share this code with participants to let them join.")
        instructions.setFont(QFont('Arial', 11))
        instructions.setStyleSheet("color: gray;")
        layout.addWidget(instructions)
        
        # Pending participants label
        pending_label = QLabel("Pending Join Requests:")
        pending_label.setFont(QFont('Arial', 12, QFont.Bold))
        layout.addWidget(pending_label)
        
        # Participants list
        self.participants_list = QListWidget()
        self.participants_list.setFont(QFont('Arial', 11))
        self.participants_list.setMinimumHeight(200)
        layout.addWidget(self.participants_list)
        
        # Action buttons for selected participant
        actions_layout = QHBoxLayout()
        
        self.allow_btn = QPushButton("✓ Allow")
        self.allow_btn.setFont(QFont('Arial', 12))
        self.allow_btn.setMinimumHeight(40)
        self.allow_btn.setStyleSheet("""
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
        self.allow_btn.clicked.connect(self.on_allow)
        
        self.deny_btn = QPushButton("✗ Deny")
        self.deny_btn.setFont(QFont('Arial', 12))
        self.deny_btn.setMinimumHeight(40)
        self.deny_btn.setStyleSheet("""
            QPushButton {
                background-color: #ea4335;
                color: white;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #d33426;
            }
        """)
        self.deny_btn.clicked.connect(self.on_deny)
        
        actions_layout.addWidget(self.allow_btn)
        actions_layout.addWidget(self.deny_btn)
        layout.addLayout(actions_layout)
        
        layout.addStretch()
        
        # Start meeting button
        self.start_btn = QPushButton("Start Meeting")
        self.start_btn.setFont(QFont('Arial', 14, QFont.Bold))
        self.start_btn.setMinimumHeight(60)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #4285f4;
                color: white;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #3367d6;
            }
        """)
        self.start_btn.clicked.connect(self.on_start_meeting)
        layout.addWidget(self.start_btn)
        
        self.setLayout(layout)
    
    def add_pending_participant(self, name):
        """Add a pending participant to the list"""
        if name not in self.pending_participants:
            self.pending_participants.append(name)
            self.participants_list.addItem(name)
            
            # Show notification
            QMessageBox.information(self, "Join Request", 
                                   f"{name} wants to join the meeting")
    
    def on_allow(self):
        """Allow selected participant"""
        current_item = self.participants_list.currentItem()
        if current_item:
            name = current_item.text()
            print(f"[WaitingRoom] Allowing participant: {name}")
            self.allow_participant_signal.emit(name)
            
            # Remove from list
            row = self.participants_list.row(current_item)
            self.participants_list.takeItem(row)
            self.pending_participants.remove(name)
        else:
            print("[WaitingRoom] No participant selected to allow")
    
    def on_deny(self):
        """Deny selected participant"""
        current_item = self.participants_list.currentItem()
        if current_item:
            name = current_item.text()
            self.deny_participant_signal.emit(name)
            
            # Remove from list
            row = self.participants_list.row(current_item)
            self.participants_list.takeItem(row)
            self.pending_participants.remove(name)
    
    def on_start_meeting(self):
        """Start the meeting"""
        self.start_meeting_signal.emit()
