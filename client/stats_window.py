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
            
            # Debug: Print stats to verify they're being collected
            print(f"[StatsWindow] Updating graphs - RTT: {current['rtt_ms']:.1f}ms, "
                  f"Loss: {current['packet_loss_percent']:.2f}%, "
                  f"Jitter: {current['jitter_ms']:.2f}ms, "
                  f"FPS: {current['fps_sent']:.1f}, "
                  f"Bitrate: {current['bitrate_kbps']:.0f}kbps")
            
            # Update labels
            self.rtt_label.setText(f"RTT: {current['rtt_ms']:.1f} ms")
            self.loss_label.setText(f"Loss: {current['packet_loss_percent']:.2f} %")
            self.jitter_label.setText(f"Jitter: {current['jitter_ms']:.2f} ms")
            self.fps_label.setText(f"FPS: {current['fps_sent']:.1f}")
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
            if history['rtt'] and len(history['rtt']) > 0:
                x = list(range(len(history['rtt'])))
                self.ax_rtt.plot(x, history['rtt'], 'b-', linewidth=2)
                self.ax_rtt.set_title(f"RTT (ms) - Current: {current['rtt_ms']:.1f}")
                max_val = max(history['rtt'])
                self.ax_rtt.set_ylim(0, max_val * 1.2 if max_val > 0 else 100)
            else:
                self.ax_rtt.text(0.5, 0.5, 'Collecting data...', 
                                ha='center', va='center', transform=self.ax_rtt.transAxes)
                self.ax_rtt.set_title('RTT (ms)')
            
            # Plot Packet Loss
            if history['packet_loss'] and len(history['packet_loss']) > 0:
                x = list(range(len(history['packet_loss'])))
                self.ax_loss.plot(x, history['packet_loss'], 'r-', linewidth=2)
                self.ax_loss.set_title(f"Packet Loss (%) - Current: {current['packet_loss_percent']:.2f}")
                self.ax_loss.set_ylim(0, 100)
            else:
                self.ax_loss.text(0.5, 0.5, 'Collecting data...', 
                                 ha='center', va='center', transform=self.ax_loss.transAxes)
                self.ax_loss.set_title('Packet Loss (%)')
            
            # Plot Jitter
            if history['jitter'] and len(history['jitter']) > 0:
                x = list(range(len(history['jitter'])))
                self.ax_jitter.plot(x, history['jitter'], 'g-', linewidth=2)
                self.ax_jitter.set_title(f"Jitter (ms) - Current: {current['jitter_ms']:.2f}")
                max_val = max(history['jitter'])
                self.ax_jitter.set_ylim(0, max_val * 1.2 if max_val > 0 else 50)
            else:
                self.ax_jitter.text(0.5, 0.5, 'Collecting data...', 
                                   ha='center', va='center', transform=self.ax_jitter.transAxes)
                self.ax_jitter.set_title('Jitter (ms)')
            
            # Plot FPS
            if history['fps'] and len(history['fps']) > 0:
                x = list(range(len(history['fps'])))
                self.ax_fps.plot(x, history['fps'], 'm-', linewidth=2)
                self.ax_fps.set_title(f"FPS - Current: {current['fps_sent']:.1f}")
                self.ax_fps.set_ylim(0, 30)
            else:
                self.ax_fps.text(0.5, 0.5, 'Collecting data...', 
                                ha='center', va='center', transform=self.ax_fps.transAxes)
                self.ax_fps.set_title('FPS')
            
            # Plot Bitrate
            if history['bitrate'] and len(history['bitrate']) > 0:
                x = list(range(len(history['bitrate'])))
                self.ax_bitrate.plot(x, history['bitrate'], 'c-', linewidth=2)
                self.ax_bitrate.set_title(f"Bitrate (kbps) - Current: {current['bitrate_kbps']:.0f}")
                max_val = max(history['bitrate'])
                self.ax_bitrate.set_ylim(0, max_val * 1.2 if max_val > 0 else 1000)
            else:
                self.ax_bitrate.text(0.5, 0.5, 'Collecting data...', 
                                    ha='center', va='center', transform=self.ax_bitrate.transAxes)
                self.ax_bitrate.set_title('Bitrate (kbps)')
            
            # Plot cwnd (if file transfer active)
            if self.file_transfer:
                stats = self.file_transfer.get_stats()
                cwnd_history = stats.get('cwnd_history', [])
                if cwnd_history:
                    x = list(range(len(cwnd_history)))
                    self.ax_cwnd.plot(x, cwnd_history, 'orange', linewidth=2, label='cwnd')
                    
                    # Also plot ssthresh if available
                    ssthresh = stats.get('ssthresh', 0)
                    if ssthresh > 0:
                        self.ax_cwnd.axhline(y=ssthresh, color='gray', linestyle='--', alpha=0.7, label='ssthresh')
                        self.ax_cwnd.text(0, ssthresh + 0.5, f'ssthresh ({ssthresh})', color='gray', fontsize=8)

                    timeout_val = stats.get('timeout_interval', 2.0)
                    self.ax_cwnd.set_title(f"Congestion Window: {stats.get('cwnd', 0):.2f} (TO: {timeout_val:.2f}s)")
                    self.ax_cwnd.set_ylim(0, max(max(cwnd_history), 20) * 1.2)
                    self.ax_cwnd.legend(loc='upper left', fontsize='small')
                else:
                    self.ax_cwnd.text(0.5, 0.5, 'Starting transfer...', 
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
