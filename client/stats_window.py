"""
Stats Window - Real-time statistics visualization with Matplotlib
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import QTimer
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class StatsWindow(QDialog):
    """Real-time statistics visualization window"""
    
    def __init__(self, stats_collector, file_transfer=None):
        super().__init__()
        self.stats_collector = stats_collector
        self.file_transfer = file_transfer
        
        self.setWindowTitle("Network Statistics")
        self.setGeometry(100, 100, 1200, 800)
        
        self.setup_ui()
        
        # Update timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_graphs)
        self.timer.start(1000)  # Update every second
    
    def setup_ui(self):
        """Setup the UI layout"""
        layout = QVBoxLayout()
        
        # Current stats labels
        stats_layout = QHBoxLayout()
        self.rtt_label = QLabel("RTT: -- ms")
        self.loss_label = QLabel("Loss: -- %")
        self.jitter_label = QLabel("Jitter: -- ms")
        self.fps_label = QLabel("FPS: --")
        self.bitrate_label = QLabel("Bitrate: -- kbps")
        
        stats_layout.addWidget(self.rtt_label)
        stats_layout.addWidget(self.loss_label)
        stats_layout.addWidget(self.jitter_label)
        stats_layout.addWidget(self.fps_label)
        stats_layout.addWidget(self.bitrate_label)
        
        layout.addLayout(stats_layout)
        
        # Matplotlib figure
        self.figure = Figure(figsize=(12, 8))
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)
        
        # Create subplots
        self.ax_rtt = self.figure.add_subplot(3, 2, 1)
        self.ax_loss = self.figure.add_subplot(3, 2, 2)
        self.ax_jitter = self.figure.add_subplot(3, 2, 3)
        self.ax_fps = self.figure.add_subplot(3, 2, 4)
        self.ax_bitrate = self.figure.add_subplot(3, 2, 5)
        self.ax_cwnd = self.figure.add_subplot(3, 2, 6)
        
        # Set titles
        self.ax_rtt.set_title('RTT (ms)')
        self.ax_loss.set_title('Packet Loss (%)')
        self.ax_jitter.set_title('Jitter (ms)')
        self.ax_fps.set_title('FPS')
        self.ax_bitrate.set_title('Bitrate (kbps)')
        self.ax_cwnd.set_title('Congestion Window (cwnd)')
        
        # Set labels
        for ax in [self.ax_rtt, self.ax_loss, self.ax_jitter, 
                   self.ax_fps, self.ax_bitrate, self.ax_cwnd]:
            ax.set_xlabel('Time (s)')
            ax.grid(True, alpha=0.3)
        
        self.figure.tight_layout()
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)
        
        self.setLayout(layout)
    
    def update_graphs(self):
        """Update all graphs with latest data"""
        try:
            # Get current stats
            current = self.stats_collector.get_current_stats()
            
            # Update labels
            self.rtt_label.setText(f"RTT: {current['rtt_ms']:.1f} ms")
            self.loss_label.setText(f"Loss: {current['packet_loss_percent']:.1f} %")
            self.jitter_label.setText(f"Jitter: {current['jitter_ms']:.1f} ms")
            self.fps_label.setText(f"FPS: {current['fps_received']:.1f}")
            self.bitrate_label.setText(f"Bitrate: {current['bitrate_kbps']:.0f} kbps")
            
            # Get history
            history = self.stats_collector.get_stats_history()
            
            # Clear all axes
            self.ax_rtt.clear()
            self.ax_loss.clear()
            self.ax_jitter.clear()
            self.ax_fps.clear()
            self.ax_bitrate.clear()
            self.ax_cwnd.clear()
            
            # Plot RTT
            if history['rtt']:
                x = list(range(len(history['rtt'])))
                self.ax_rtt.plot(x, history['rtt'], 'b-', linewidth=2)
                self.ax_rtt.set_title(f"RTT (ms) - Current: {current['rtt_ms']:.1f}")
                self.ax_rtt.set_ylim(0, max(history['rtt']) * 1.2 if history['rtt'] else 100)
            
            # Plot Packet Loss
            if history['packet_loss']:
                x = list(range(len(history['packet_loss'])))
                self.ax_loss.plot(x, history['packet_loss'], 'r-', linewidth=2)
                self.ax_loss.set_title(f"Packet Loss (%) - Current: {current['packet_loss_percent']:.1f}")
                self.ax_loss.set_ylim(0, 100)
            
            # Plot Jitter
            if history['jitter']:
                x = list(range(len(history['jitter'])))
                self.ax_jitter.plot(x, history['jitter'], 'g-', linewidth=2)
                self.ax_jitter.set_title(f"Jitter (ms) - Current: {current['jitter_ms']:.1f}")
                self.ax_jitter.set_ylim(0, max(history['jitter']) * 1.2 if history['jitter'] else 50)
            
            # Plot FPS
            if history['fps']:
                x = list(range(len(history['fps'])))
                self.ax_fps.plot(x, history['fps'], 'm-', linewidth=2)
                self.ax_fps.set_title(f"FPS - Current: {current['fps_received']:.1f}")
                self.ax_fps.set_ylim(0, 30)
            
            # Plot Bitrate
            if history['bitrate']:
                x = list(range(len(history['bitrate'])))
                self.ax_bitrate.plot(x, history['bitrate'], 'c-', linewidth=2)
                self.ax_bitrate.set_title(f"Bitrate (kbps) - Current: {current['bitrate_kbps']:.0f}")
                self.ax_bitrate.set_ylim(0, max(history['bitrate']) * 1.2 if history['bitrate'] else 1000)
            
            # Plot cwnd (if file transfer active)
            if self.file_transfer:
                stats = self.file_transfer.get_stats()
                cwnd_history = stats.get('cwnd_history', [])
                if cwnd_history:
                    x = list(range(len(cwnd_history)))
                    self.ax_cwnd.plot(x, cwnd_history, 'orange', linewidth=2)
                    self.ax_cwnd.set_title(f"Congestion Window - Current: {stats.get('cwnd', 0)}")
                    self.ax_cwnd.set_ylim(0, max(cwnd_history) * 1.2)
                else:
                    self.ax_cwnd.text(0.5, 0.5, 'No file transfer', 
                                     ha='center', va='center', transform=self.ax_cwnd.transAxes)
            else:
                self.ax_cwnd.text(0.5, 0.5, 'No file transfer', 
                                 ha='center', va='center', transform=self.ax_cwnd.transAxes)
            
            # Re-enable grids
            for ax in [self.ax_rtt, self.ax_loss, self.ax_jitter, 
                      self.ax_fps, self.ax_bitrate, self.ax_cwnd]:
                ax.grid(True, alpha=0.3)
                ax.set_xlabel('Time (s)')
            
            self.figure.tight_layout()
            self.canvas.draw()
        
        except Exception as e:
            print(f"[StatsWindow] Error updating graphs: {e}")
    
    def closeEvent(self, event):
        """Handle window close event"""
        self.timer.stop()
        event.accept()
