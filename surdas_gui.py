"""
SURDAS PyQt5 GUI Application
Modern desktop interface for SURDAS assistive vision system
"""

import sys
import os
import cv2
import numpy as np
import time
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTextEdit, QGroupBox, QGridLayout,
    QFrame, QScrollArea, QSizePolicy, QSpacerItem, QTabWidget
)
from PyQt5.QtCore import Qt, QTimer, QTime, pyqtSignal, QThread, QSize
from PyQt5.QtGui import QImage, QPixmap, QFont, QPalette, QColor, QIcon

# Add parent directory to path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from surdas_brain import SurdasBrain


class BrainThread(QThread):
    """Background thread for running SURDAS brain"""
    log_signal = pyqtSignal(str, str)  # (type, message)
    
    def __init__(self, brain):
        super().__init__()
        self.brain = brain
        self.brain.headless = False  # GUI mode
        
    def run(self):
        """Run the brain in background thread"""
        self.brain.run()


class ModernButton(QPushButton):
    """Custom styled button with modern appearance"""
    
    def __init__(self, text, color="blue", parent=None):
        super().__init__(text, parent)
        self.color = color
        self.update_style()
        self.setMinimumHeight(45)
        self.setCursor(Qt.PointingHandCursor)
        
    def update_style(self, active=False):
        """Update button style based on state"""
        colors = {
            "blue": ("#3b82f6", "#2563eb", "#1d4ed8"),
            "green": ("#10b981", "#059669", "#047857"),
            "purple": ("#8b5cf6", "#7c3aed", "#6d28d9"),
            "red": ("#ef4444", "#dc2626", "#b91c1c"),
            "gray": ("#6b7280", "#4b5563", "#374151"),
        }
        
        base, hover, active_color = colors.get(self.color, colors["blue"])
        
        if active:
            bg = active_color
        else:
            bg = base
            
        self.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {bg}, stop:1 {hover});
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {hover}, stop:1 {active_color});
            }}
            QPushButton:pressed {{
                background: {active_color};
            }}
            QPushButton:disabled {{
                background: #9ca3af;
                color: #d1d5db;
            }}
        """)


class StatusBadge(QLabel):
    """Status indicator badge"""
    
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setAlignment(Qt.AlignCenter)
        self.setFixedHeight(32)
        self.update_status("disconnected")
        
    def update_status(self, status):
        """Update badge appearance based on status"""
        styles = {
            "connected": ("🟢 Connected", "#ecfdf5", "#065f46"),
            "active": ("🔵 Active", "#eff6ff", "#1e40af"),
            "navigating": ("🧭 Navigating", "#fef3c7", "#92400e"),
            "warning": ("⚠️ Warning", "#fef2f2", "#991b1b"),
            "disconnected": ("⚪ Disconnected", "#f3f4f6", "#6b7280"),
        }
        
        text, bg, fg = styles.get(status, styles["disconnected"])
        self.setText(text)
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {bg};
                color: {fg};
                border-radius: 16px;
                padding: 6px 20px;
                font-weight: 600;
                font-size: 13px;
            }}
        """)


class InfoCard(QGroupBox):
    """Modern card widget for displaying information"""
    
    def __init__(self, title, parent=None):
        super().__init__(title, parent)
        self.setStyleSheet("""
            QGroupBox {
                background-color: white;
                border: 1px solid #e5e7eb;
                border-radius: 12px;
                padding: 20px;
                margin-top: 12px;
                font-weight: 600;
                font-size: 15px;
                color: #111827;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                background-color: white;
                color: #374151;
            }
        """)


class VideoDisplay(QLabel):
    """Video feed display widget"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(640, 480)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("""
            QLabel {
                background-color: #1f2937;
                border: 2px solid #374151;
                border-radius: 12px;
                color: #9ca3af;
                font-size: 14px;
            }
        """)
        self.setText("📹 Camera Feed\n\nWaiting for video stream...")
        
    def update_frame(self, frame):
        """Update video frame"""
        if frame is not None:
            # Convert BGR to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_frame.shape
            bytes_per_line = ch * w
            qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
            
            # Scale to fit while maintaining aspect ratio
            pixmap = QPixmap.fromImage(qt_image)
            scaled_pixmap = pixmap.scaled(
                self.width() - 4, self.height() - 4,
                Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.setPixmap(scaled_pixmap)


class LogDisplay(QTextEdit):
    """Styled log display widget"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setMinimumHeight(200)
        self.setStyleSheet("""
            QTextEdit {
                background-color: #f9fafb;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                padding: 12px;
                font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
                font-size: 12px;
                color: #374151;
            }
        """)
        
    def add_log(self, log_type, message):
        """Add formatted log entry"""
        color_map = {
            "info": "#3b82f6",
            "success": "#10b981",
            "warning": "#f59e0b",
            "error": "#ef4444",
            "speech": "#8b5cf6",
            "navigation": "#06b6d4",
        }
        
        color = color_map.get(log_type, "#6b7280")
        timestamp = QTime.currentTime().toString("hh:mm:ss")
        
        html = f'<span style="color: #9ca3af;">[{timestamp}]</span> '
        html += f'<span style="color: {color}; font-weight: 600;">[{log_type.upper()}]</span> '
        html += f'<span style="color: #111827;">{message}</span>'
        
        self.append(html)
        # Auto-scroll to bottom
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())


class SurdasGUI(QMainWindow):
    """Main SURDAS GUI Application"""
    
    def __init__(self):
        super().__init__()
        
        # Initialize brain
        self.brain = None
        self.brain_thread = None
        
        # Setup UI
        self.init_ui()
        
        # Setup update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_display)
        self.update_timer.start(50)  # 20 FPS
        
    def init_ui(self):
        """Initialize user interface"""
        self.setWindowTitle("SURDAS - Assistive Vision System")
        self.setMinimumSize(1400, 900)
        
        # Apply modern theme
        self.apply_theme()
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # ─── Header ───
        header = self.create_header()
        main_layout.addWidget(header)
        
        # ─── Main Content (3 columns) ───
        content_layout = QHBoxLayout()
        content_layout.setSpacing(16)
        
        # Left column: Video & Vision
        left_column = self.create_left_column()
        content_layout.addWidget(left_column, stretch=2)
        
        # Middle column: Controls & Status
        middle_column = self.create_middle_column()
        content_layout.addWidget(middle_column, stretch=1)
        
        # Right column: Navigation & Memory
        right_column = self.create_right_column()
        content_layout.addWidget(right_column, stretch=1)
        
        main_layout.addLayout(content_layout, stretch=1)
        
        # ─── Footer: Logs ───
        footer = self.create_footer()
        main_layout.addWidget(footer)
        
    def apply_theme(self):
        """Apply modern color theme"""
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor("#f0f4f8"))
        palette.setColor(QPalette.WindowText, QColor("#1a202c"))
        palette.setColor(QPalette.Base, QColor("#ffffff"))
        palette.setColor(QPalette.AlternateBase, QColor("#f9fafb"))
        palette.setColor(QPalette.ToolTipBase, QColor("#1f2937"))
        palette.setColor(QPalette.ToolTipText, QColor("#f3f4f6"))
        palette.setColor(QPalette.Text, QColor("#111827"))
        palette.setColor(QPalette.Button, QColor("#ffffff"))
        palette.setColor(QPalette.ButtonText, QColor("#374151"))
        
        self.setPalette(palette)
        
        # Global stylesheet
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f4f8;
            }
            QLabel {
                color: #374151;
            }
            * {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            }
        """)
        
    def create_header(self):
        """Create header with branding and status"""
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3b82f6, stop:1 #6366f1);
                border-radius: 12px;
                padding: 20px;
            }
        """)
        header.setFixedHeight(80)
        
        layout = QHBoxLayout(header)
        
        # Branding
        title = QLabel("🛡️ SURDAS")
        title.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 28px;
                font-weight: 700;
            }
        """)
        layout.addWidget(title)
        
        subtitle = QLabel("Assistive Vision System")
        subtitle.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.9);
                font-size: 14px;
            }
        """)
        layout.addWidget(subtitle)
        
        layout.addStretch()
        
        # Status badge
        self.status_badge = StatusBadge()
        layout.addWidget(self.status_badge)
        
        return header
        
    def create_left_column(self):
        """Create left column with video and vision info"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(12)
        
        # Video feed
        video_card = InfoCard("📹 Live Camera Feed")
        video_layout = QVBoxLayout()
        self.video_display = VideoDisplay()
        video_layout.addWidget(self.video_display)
        video_card.setLayout(video_layout)
        layout.addWidget(video_card, stretch=3)
        
        # Vision state
        vision_card = InfoCard("👁️ Vision State")
        vision_layout = QGridLayout()
        
        # Mode
        vision_layout.addWidget(QLabel("Mode:"), 0, 0)
        self.mode_label = QLabel("IDLE")
        self.mode_label.setStyleSheet("font-weight: 600; color: #3b82f6;")
        vision_layout.addWidget(self.mode_label, 0, 1)
        
        # Flashlight
        vision_layout.addWidget(QLabel("Flashlight:"), 1, 0)
        self.torch_label = QLabel("OFF")
        self.torch_label.setStyleSheet("font-weight: 600; color: #6b7280;")
        vision_layout.addWidget(self.torch_label, 1, 1)
        
        # Closest obstacle
        vision_layout.addWidget(QLabel("Closest:"), 2, 0)
        self.obstacle_label = QLabel("—")
        self.obstacle_label.setStyleSheet("font-weight: 600; color: #111827;")
        vision_layout.addWidget(self.obstacle_label, 2, 1)
        
        # Wall detection
        vision_layout.addWidget(QLabel("Wall Ahead:"), 3, 0)
        self.wall_label = QLabel("NO")
        self.wall_label.setStyleSheet("font-weight: 600; color: #10b981;")
        vision_layout.addWidget(self.wall_label, 3, 1)
        
        vision_card.setLayout(vision_layout)
        layout.addWidget(vision_card, stretch=1)
        
        return widget
        
    def create_middle_column(self):
        """Create middle column with controls"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(12)
        
        # System controls
        controls_card = InfoCard("🎛️ System Controls")
        controls_layout = QVBoxLayout()
        controls_layout.setSpacing(10)
        
        self.start_btn = ModernButton("▶️ Start System", "green")
        self.start_btn.clicked.connect(self.start_system)
        controls_layout.addWidget(self.start_btn)
        
        self.stop_btn = ModernButton("⏹️ Stop System", "red")
        self.stop_btn.clicked.connect(self.stop_system)
        self.stop_btn.setEnabled(False)
        controls_layout.addWidget(self.stop_btn)
        
        controls_layout.addSpacing(10)
        
        # Mode controls
        mode_label = QLabel("Operating Modes:")
        mode_label.setStyleSheet("font-weight: 600; margin-top: 10px;")
        controls_layout.addWidget(mode_label)
        
        self.nav_btn = ModernButton("🧭 Navigation", "blue")
        self.nav_btn.clicked.connect(lambda: self.set_mode("NAV"))
        self.nav_btn.setEnabled(False)
        controls_layout.addWidget(self.nav_btn)
        
        self.ocr_btn = ModernButton("📖 Text Reading", "purple")
        self.ocr_btn.clicked.connect(lambda: self.set_mode("OCR"))
        self.ocr_btn.setEnabled(False)
        controls_layout.addWidget(self.ocr_btn)
        
        self.currency_btn = ModernButton("💵 Currency", "green")
        self.currency_btn.clicked.connect(lambda: self.set_mode("CURRENCY"))
        self.currency_btn.setEnabled(False)
        controls_layout.addWidget(self.currency_btn)
        
        controls_layout.addSpacing(10)
        
        # Hardware controls
        hw_label = QLabel("Hardware:")
        hw_label.setStyleSheet("font-weight: 600; margin-top: 10px;")
        controls_layout.addWidget(hw_label)
        
        self.torch_btn = ModernButton("🔦 Toggle Flashlight", "gray")
        self.torch_btn.clicked.connect(self.toggle_torch)
        self.torch_btn.setEnabled(False)
        controls_layout.addWidget(self.torch_btn)
        
        controls_layout.addStretch()
        controls_card.setLayout(controls_layout)
        layout.addWidget(controls_card)
        
        # Statistics
        stats_card = InfoCard("📊 Statistics")
        stats_layout = QGridLayout()
        
        stats_layout.addWidget(QLabel("FPS:"), 0, 0)
        self.fps_label = QLabel("0")
        self.fps_label.setStyleSheet("font-weight: 600; color: #3b82f6;")
        stats_layout.addWidget(self.fps_label, 0, 1)
        
        stats_layout.addWidget(QLabel("Objects:"), 1, 0)
        self.objects_count_label = QLabel("0")
        self.objects_count_label.setStyleSheet("font-weight: 600; color: #8b5cf6;")
        stats_layout.addWidget(self.objects_count_label, 1, 1)
        
        stats_layout.addWidget(QLabel("Uptime:"), 2, 0)
        self.uptime_label = QLabel("00:00:00")
        self.uptime_label.setStyleSheet("font-weight: 600; color: #10b981;")
        stats_layout.addWidget(self.uptime_label, 2, 1)
        
        stats_card.setLayout(stats_layout)
        layout.addWidget(stats_card)
        
        return widget
        
    def create_right_column(self):
        """Create right column with navigation and memory"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(12)
        
        # Indoor navigation
        nav_card = InfoCard("🧭 Indoor Navigation")
        nav_layout = QGridLayout()
        
        nav_layout.addWidget(QLabel("State:"), 0, 0)
        self.nav_state_label = QLabel("IDLE")
        self.nav_state_label.setStyleSheet("font-weight: 600; color: #6b7280;")
        nav_layout.addWidget(self.nav_state_label, 0, 1)
        
        nav_layout.addWidget(QLabel("Destination:"), 1, 0)
        self.nav_dest_label = QLabel("—")
        self.nav_dest_label.setStyleSheet("font-weight: 600;")
        nav_layout.addWidget(self.nav_dest_label, 1, 1)
        
        nav_layout.addWidget(QLabel("Confidence:"), 2, 0)
        self.nav_conf_label = QLabel("—")
        self.nav_conf_label.setStyleSheet("font-weight: 600;")
        nav_layout.addWidget(self.nav_conf_label, 2, 1)
        
        nav_layout.addWidget(QLabel("Safe Paths:"), 3, 0)
        self.nav_safe_label = QLabel("0")
        self.nav_safe_label.setStyleSheet("font-weight: 600;")
        nav_layout.addWidget(self.nav_safe_label, 3, 1)
        
        nav_card.setLayout(nav_layout)
        layout.addWidget(nav_card)
        
        # Detected objects
        objects_card = InfoCard("🔍 Detected Objects")
        objects_layout = QVBoxLayout()
        
        self.objects_display = QTextEdit()
        self.objects_display.setReadOnly(True)
        self.objects_display.setMaximumHeight(150)
        self.objects_display.setStyleSheet("""
            QTextEdit {
                background-color: #f9fafb;
                border: 1px solid #e5e7eb;
                border-radius: 6px;
                padding: 8px;
                font-size: 12px;
            }
        """)
        self.objects_display.setPlaceholderText("No objects detected yet...")
        objects_layout.addWidget(self.objects_display)
        
        objects_card.setLayout(objects_layout)
        layout.addWidget(objects_card)
        
        # Spatial memory
        memory_card = InfoCard("🧠 Spatial Memory")
        memory_layout = QVBoxLayout()
        
        self.memory_display = QTextEdit()
        self.memory_display.setReadOnly(True)
        self.memory_display.setMaximumHeight(200)
        self.memory_display.setStyleSheet("""
            QTextEdit {
                background-color: #f9fafb;
                border: 1px solid #e5e7eb;
                border-radius: 6px;
                padding: 8px;
                font-size: 12px;
            }
        """)
        self.memory_display.setPlaceholderText("No spatial memory stored yet...")
        memory_layout.addWidget(self.memory_display)
        
        memory_card.setLayout(memory_layout)
        layout.addWidget(memory_card)
        
        layout.addStretch()
        
        return widget
        
    def create_footer(self):
        """Create footer with activity logs"""
        footer_card = InfoCard("📜 Activity Logs")
        footer_layout = QVBoxLayout()
        
        self.log_display = LogDisplay()
        footer_layout.addWidget(self.log_display)
        
        # Log controls
        log_controls = QHBoxLayout()
        
        clear_btn = ModernButton("Clear Logs", "gray")
        clear_btn.setMaximumWidth(150)
        clear_btn.clicked.connect(self.log_display.clear)
        log_controls.addWidget(clear_btn)
        
        log_controls.addStretch()
        footer_layout.addLayout(log_controls)
        
        footer_card.setLayout(footer_layout)
        return footer_card
        
    # ─── Control Methods ───
    
    def start_system(self):
        """Start SURDAS system"""
        if self.brain is None:
            self.log_display.add_log("info", "Initializing SURDAS brain...")
            self.brain = SurdasBrain()
            self.brain.headless = False
            
            # Start brain thread
            self.brain_thread = BrainThread(self.brain)
            self.brain_thread.start()
            
            # Update UI
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.nav_btn.setEnabled(True)
            self.ocr_btn.setEnabled(True)
            self.currency_btn.setEnabled(True)
            self.torch_btn.setEnabled(True)
            self.status_badge.update_status("connected")
            
            self.log_display.add_log("success", "✅ System started successfully")
            self.start_time = time.time()
            
    def stop_system(self):
        """Stop SURDAS system"""
        if self.brain:
            self.log_display.add_log("info", "Stopping system...")
            self.brain.should_stop = True
            
            if self.brain_thread:
                self.brain_thread.wait(2000)  # Wait up to 2 seconds
                
            self.brain = None
            self.brain_thread = None
            
            # Update UI
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.nav_btn.setEnabled(False)
            self.ocr_btn.setEnabled(False)
            self.currency_btn.setEnabled(False)
            self.torch_btn.setEnabled(False)
            self.status_badge.update_status("disconnected")
            
            self.log_display.add_log("info", "⏹️ System stopped")
            
    def set_mode(self, mode):
        """Set operating mode"""
        if self.brain:
            self.brain.mode = mode
            self.log_display.add_log("info", f"Mode changed to: {mode}")
            
            # Update button states
            self.nav_btn.update_style(mode == "NAV")
            self.ocr_btn.update_style(mode == "OCR")
            self.currency_btn.update_style(mode == "CURRENCY")
            
    def toggle_torch(self):
        """Toggle flashlight"""
        if self.brain:
            self.brain.toggle_esp32_led(not self.brain.led_on)
            self.log_display.add_log("info", f"Flashlight {'ON' if self.brain.led_on else 'OFF'}")
            
    def update_display(self):
        """Update display with latest data"""
        if self.brain:
            # Update video
            if hasattr(self.brain, 'latest_display_frame') and self.brain.latest_display_frame is not None:
                self.video_display.update_frame(self.brain.latest_display_frame)
                
            # Update vision state
            self.mode_label.setText(self.brain.mode)
            self.torch_label.setText("ON" if self.brain.led_on else "OFF")
            self.torch_label.setStyleSheet(
                f"font-weight: 600; color: {'#f59e0b' if self.brain.led_on else '#6b7280'};"
            )
            
            # Update obstacle info
            if hasattr(self.brain, 'latest_closest_obstacle') and self.brain.latest_closest_obstacle:
                self.obstacle_label.setText(self.brain.latest_closest_obstacle)
            else:
                self.obstacle_label.setText("✅ Clear")
                
            # Update wall detection
            if hasattr(self.brain, 'wall_detected'):
                self.wall_label.setText("YES" if self.brain.wall_detected else "NO")
                color = "#ef4444" if self.brain.wall_detected else "#10b981"
                self.wall_label.setStyleSheet(f"font-weight: 600; color: {color};")
                
            # Update detected objects
            if hasattr(self.brain, 'latest_detected_objects') and self.brain.latest_detected_objects:
                objects_text = ", ".join(set(self.brain.latest_detected_objects[:10]))
                self.objects_display.setText(objects_text)
                self.objects_count_label.setText(str(len(set(self.brain.latest_detected_objects))))
            
            # Update navigation state
            if hasattr(self.brain, 'indoor_navigator') and self.brain.indoor_navigator:
                nav = self.brain.indoor_navigator
                self.nav_state_label.setText(nav.state)
                
                color_map = {
                    "IDLE": "#6b7280",
                    "NAVIGATING": "#3b82f6",
                    "SAFETY_HOLD": "#ef4444",
                    "APPROACHING": "#10b981",
                    "ARRIVED": "#059669"
                }
                self.nav_state_label.setStyleSheet(
                    f"font-weight: 600; color: {color_map.get(nav.state, '#6b7280')};"
                )
                
                self.nav_dest_label.setText(nav.destination or "—")
                
                if hasattr(self.brain, 'indoor_perception'):
                    perc = self.brain.indoor_perception
                    if hasattr(perc, 'current_confidence'):
                        self.nav_conf_label.setText(perc.current_confidence)
                    if hasattr(perc, 'safe_direction_count'):
                        self.nav_safe_label.setText(str(perc.safe_direction_count))
            
            # Update uptime
            if hasattr(self, 'start_time'):
                uptime = int(time.time() - self.start_time)
                hours = uptime // 3600
                minutes = (uptime % 3600) // 60
                seconds = uptime % 60
                self.uptime_label.setText(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
                
            # Update status badge based on activity
            if self.brain.mode != "IDLE":
                if hasattr(self.brain, 'indoor_navigator') and self.brain.indoor_navigator.state == "NAVIGATING":
                    self.status_badge.update_status("navigating")
                else:
                    self.status_badge.update_status("active")
            else:
                self.status_badge.update_status("connected")
                
    def closeEvent(self, event):
        """Handle window close event"""
        if self.brain:
            self.stop_system()
        event.accept()


def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    
    # Set application metadata
    app.setApplicationName("SURDAS")
    app.setApplicationVersion("2.0")
    app.setOrganizationName("VNR")
    
    # Create and show main window
    window = SurdasGUI()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
