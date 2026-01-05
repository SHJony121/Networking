    def update_ping(self, rtt_ms):
        """Update the ping/RTT label with color coding"""
        self.ping_label.setText(f"Ping: {int(rtt_ms)} ms")
        
        if rtt_ms < 100:
            color = "#4CAF50"  # Green
        elif rtt_ms < 300:
            color = "#FFC107"  # Amber/Yellow
        else:
            color = "#FF5252"  # Red
            
        self.ping_label.setStyleSheet(f"color: {color}; padding-left: 15px; font-weight: bold;")
