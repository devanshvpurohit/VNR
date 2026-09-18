"""
SURDAS Tkinter GUI Application
Modern desktop interface for SURDAS assistive vision system using tkinter
"""

import sys
import os
import cv2
import numpy as np
import time
import threading
from tkinter import *
from tkinter import ttk, scrolledtext
from PIL import Image, ImageTk
from datetime import datetime

# Add parent directory to path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from surdas_brain import SurdasBrain


class BrainThread(threading.Thread):
    """Background thread for running SURDAS brain"""
    
    def __init__(self, brain, gui):
        super().__init__(daemon=True)
        self.brain = brain
        self.gui = gui
        self.brain.headless = False  # GUI mode
        
    def run(self):
        """Run the brain in background thread"""
        try:
            self.brain.run()
        except Exception as e:
            self.gui.add_log("error", f"Brain error: {str(e)}")


class SurdasGUI:
    """Main SURDAS GUI Application using tkinter"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("SURDAS - Assistive Vision System")
        self.root.geometry("1400x900")
        
        # Initialize variables
        self.brain = None
        self.brain_thread = None
        self.start_time = None
        self.video_label = None
        self.update_running = False
        
        # Color scheme
        self.colors = {
            'bg_primary': '#f0f4f8',
            'bg_card': '#ffffff',
            'bg_input': '#f9fafb',
            'text_primary': '#111827',
            'text_secondary': '#374151',
            'blue': '#3b82f6',
            'green': '#10b981',
            'red': '#ef4444',
            'purple': '#8b5cf6',
            'amber': '#f59e0b',
            'gray': '#6b7280',
        }
        
        # Configure root window
        self.root.configure(bg=self.colors['bg_primary'])
        
        # Create UI
        self.create_ui()
        
        # Start update loop
        self.update_running = True
        self.update_display()
        
    def create_ui(self):
        """Create the user interface"""
        
        # ─── Header ───
        header_frame = Frame(self.root, bg='#3b82f6', height=80)
        header_frame.pack(fill=X, padx=10, pady=(10, 5))
        header_frame.pack_propagate(False)
        
        # Header content
        header_left = Frame(header_frame, bg='#3b82f6')
        header_left.pack(side=LEFT, padx=20, pady=15)
        
        Label(header_left, text="🛡️ SURDAS", 
              font=("Arial", 24, "bold"), bg='#3b82f6', fg='white').pack(side=LEFT)
        Label(header_left, text="  Assistive Vision System", 
              font=("Arial", 12), bg='#3b82f6', fg='white').pack(side=LEFT, padx=(10, 0))
        
        # Status badge
        header_right = Frame(header_frame, bg='#3b82f6')
        header_right.pack(side=RIGHT, padx=20, pady=15)
        
        self.status_label = Label(header_right, text="⚪ Disconnected",
                                 font=("Arial", 11, "bold"),
                                 bg='#f3f4f6', fg='#6b7280',
                                 padx=15, pady=5, relief=FLAT)
        self.status_label.pack()
        
        # ─── Main Content (3 columns) ───
        content_frame = Frame(self.root, bg=self.colors['bg_primary'])
        content_frame.pack(fill=BOTH, expand=True, padx=10, pady=5)
        
        # Configure grid weights
        content_frame.columnconfigure(0, weight=2)  # Left column
        content_frame.columnconfigure(1, weight=1)  # Middle column
        content_frame.columnconfigure(2, weight=1)  # Right column
        content_frame.rowconfigure(0, weight=1)
        
        # Left Column: Video & Vision
        self.create_left_column(content_frame)
        
        # Middle Column: Controls
        self.create_middle_column(content_frame)
        
        # Right Column: Navigation & Memory
        self.create_right_column(content_frame)
        
        # ─── Footer: Logs ───
        self.create_footer()
        
    def create_card(self, parent, title):
        """Create a card widget"""
        card = Frame(parent, bg=self.colors['bg_card'], relief=SOLID, bd=1)
        
        title_label = Label(card, text=title, font=("Arial", 13, "bold"),
                          bg=self.colors['bg_card'], fg=self.colors['text_secondary'],
                          anchor=W)
        title_label.pack(fill=X, padx=15, pady=(10, 5))
        
        return card
        
    def create_left_column(self, parent):
        """Create left column with video and vision state"""
        left_frame = Frame(parent, bg=self.colors['bg_primary'])
        left_frame.grid(row=0, column=0, sticky=NSEW, padx=(0, 5))
        
        # Video card
        video_card = self.create_card(left_frame, "📹 Live Camera Feed")
        video_card.pack(fill=BOTH, expand=True, pady=(0, 5))
        
        # Video display
        video_container = Frame(video_card, bg='#1f2937')
        video_container.pack(fill=BOTH, expand=True, padx=10, pady=(5, 10))
        
        self.video_label = Label(video_container, text="📹 Camera Feed\n\nWaiting for video stream...",
                                font=("Arial", 12), bg='#1f2937', fg='#9ca3af')
        self.video_label.pack(fill=BOTH, expand=True)
        
        # Vision state card
        vision_card = self.create_card(left_frame, "👁️ Vision State")
        vision_card.pack(fill=X, pady=(0, 5))
        
        vision_content = Frame(vision_card, bg=self.colors['bg_card'])
        vision_content.pack(fill=X, padx=15, pady=(5, 10))
        
        # Vision state fields
        self.create_info_row(vision_content, "Mode:", "mode_label")
        self.create_info_row(vision_content, "Flashlight:", "torch_label")
        self.create_info_row(vision_content, "Closest:", "obstacle_label")
        self.create_info_row(vision_content, "Wall Ahead:", "wall_label")
        
    def create_middle_column(self, parent):
        """Create middle column with controls"""
        middle_frame = Frame(parent, bg=self.colors['bg_primary'])
        middle_frame.grid(row=0, column=1, sticky=NSEW, padx=5)
        
        # Controls card
        controls_card = self.create_card(middle_frame, "🎛️ System Controls")
        controls_card.pack(fill=BOTH, expand=True, pady=(0, 5))
        
        controls_content = Frame(controls_card, bg=self.colors['bg_card'])
        controls_content.pack(fill=BOTH, expand=True, padx=10, pady=(5, 10))
        
        # Start/Stop buttons
        self.start_btn = self.create_button(controls_content, "▶️ Start System",
                                           self.start_system, 'green')
        self.start_btn.pack(fill=X, pady=3)
        
        self.stop_btn = self.create_button(controls_content, "⏹️ Stop System",
                                          self.stop_system, 'red')
        self.stop_btn.pack(fill=X, pady=3)
        self.stop_btn.config(state=DISABLED)
        
        # Mode buttons
        Label(controls_content, text="Operating Modes:", font=("Arial", 10, "bold"),
              bg=self.colors['bg_card']).pack(fill=X, pady=(10, 5))
        
        self.nav_btn = self.create_button(controls_content, "🧭 Navigation",
                                         lambda: self.set_mode("NAV"), 'blue')
        self.nav_btn.pack(fill=X, pady=3)
        self.nav_btn.config(state=DISABLED)
        
        self.ocr_btn = self.create_button(controls_content, "📖 Text Reading",
                                         lambda: self.set_mode("OCR"), 'purple')
        self.ocr_btn.pack(fill=X, pady=3)
        self.ocr_btn.config(state=DISABLED)
        
        self.currency_btn = self.create_button(controls_content, "💵 Currency",
                                              lambda: self.set_mode("CURRENCY"), 'green')
        self.currency_btn.pack(fill=X, pady=3)
        self.currency_btn.config(state=DISABLED)
        
        # Hardware controls
        Label(controls_content, text="Hardware:", font=("Arial", 10, "bold"),
              bg=self.colors['bg_card']).pack(fill=X, pady=(10, 5))
        
        self.torch_btn = self.create_button(controls_content, "🔦 Toggle Flashlight",
                                           self.toggle_torch, 'gray')
        self.torch_btn.pack(fill=X, pady=3)
        self.torch_btn.config(state=DISABLED)
        
        # Statistics card
        stats_card = self.create_card(middle_frame, "📊 Statistics")
        stats_card.pack(fill=X)
        
        stats_content = Frame(stats_card, bg=self.colors['bg_card'])
        stats_content.pack(fill=X, padx=15, pady=(5, 10))
        
        self.create_info_row(stats_content, "FPS:", "fps_label")
        self.create_info_row(stats_content, "Objects:", "objects_count_label")
        self.create_info_row(stats_content, "Uptime:", "uptime_label")
        
    def create_right_column(self, parent):
        """Create right column with navigation and memory"""
        right_frame = Frame(parent, bg=self.colors['bg_primary'])
        right_frame.grid(row=0, column=2, sticky=NSEW, padx=(5, 0))
        
        # Indoor navigation card
        nav_card = self.create_card(right_frame, "🧭 Indoor Navigation")
        nav_card.pack(fill=X, pady=(0, 5))
        
        nav_content = Frame(nav_card, bg=self.colors['bg_card'])
        nav_content.pack(fill=X, padx=15, pady=(5, 10))
        
        self.create_info_row(nav_content, "State:", "nav_state_label")
        self.create_info_row(nav_content, "Destination:", "nav_dest_label")
        self.create_info_row(nav_content, "Confidence:", "nav_conf_label")
        self.create_info_row(nav_content, "Safe Paths:", "nav_safe_label")
        
        # Detected objects card
        objects_card = self.create_card(right_frame, "🔍 Detected Objects")
        objects_card.pack(fill=BOTH, expand=True, pady=(0, 5))
        
        self.objects_text = scrolledtext.ScrolledText(objects_card, height=6,
                                                      bg=self.colors['bg_input'],
                                                      font=("Arial", 10),
                                                      wrap=WORD, state=DISABLED)
        self.objects_text.pack(fill=BOTH, expand=True, padx=10, pady=(5, 10))
        
        # Spatial memory card
        memory_card = self.create_card(right_frame, "🧠 Spatial Memory")
        memory_card.pack(fill=BOTH, expand=True)
        
        self.memory_text = scrolledtext.ScrolledText(memory_card, height=6,
                                                     bg=self.colors['bg_input'],
                                                     font=("Arial", 10),
                                                     wrap=WORD, state=DISABLED)
        self.memory_text.pack(fill=BOTH, expand=True, padx=10, pady=(5, 10))
        
    def create_footer(self):
        """Create footer with logs"""
        footer_card = Frame(self.root, bg=self.colors['bg_card'], relief=SOLID, bd=1)
        footer_card.pack(fill=BOTH, padx=10, pady=(5, 10), expand=False)
        
        # Header
        header = Frame(footer_card, bg=self.colors['bg_card'])
        header.pack(fill=X, padx=15, pady=(10, 5))
        
        Label(header, text="📜 Activity Logs", font=("Arial", 13, "bold"),
              bg=self.colors['bg_card'], fg=self.colors['text_secondary']).pack(side=LEFT)
        
        clear_btn = Button(header, text="Clear Logs", command=self.clear_logs,
                          font=("Arial", 9), bg='#e5e7eb', fg='#374151',
                          relief=FLAT, padx=10, pady=3)
        clear_btn.pack(side=RIGHT)
        
        # Logs display
        self.log_text = scrolledtext.ScrolledText(footer_card, height=8,
                                                  bg=self.colors['bg_input'],
                                                  font=("Courier", 10),
                                                  wrap=WORD, state=DISABLED)
        self.log_text.pack(fill=BOTH, expand=True, padx=10, pady=(0, 10))
        
        # Configure log tags for coloring
        self.log_text.tag_config("info", foreground="#3b82f6")
        self.log_text.tag_config("success", foreground="#10b981")
        self.log_text.tag_config("warning", foreground="#f59e0b")
        self.log_text.tag_config("error", foreground="#ef4444")
        self.log_text.tag_config("speech", foreground="#8b5cf6")
        self.log_text.tag_config("navigation", foreground="#06b6d4")
        self.log_text.tag_config("timestamp", foreground="#9ca3af")
        
    def create_button(self, parent, text, command, color):
        """Create a styled button"""
        color_map = {
            'blue': ('#3b82f6', 'white'),
            'green': ('#10b981', 'white'),
            'red': ('#ef4444', 'white'),
            'purple': ('#8b5cf6', 'white'),
            'gray': ('#6b7280', 'white'),
        }
        
        bg, fg = color_map.get(color, ('#3b82f6', 'white'))
        
        btn = Button(parent, text=text, command=command, font=("Arial", 11, "bold"),
                    bg=bg, fg=fg, relief=FLAT, padx=10, pady=8, cursor="hand2")
        return btn
        
    def create_info_row(self, parent, label_text, var_name):
        """Create an info row with label and value"""
        row = Frame(parent, bg=self.colors['bg_input'])
        row.pack(fill=X, pady=3)
        
        Label(row, text=label_text, font=("Arial", 10),
              bg=self.colors['bg_input'], fg=self.colors['text_secondary'],
              anchor=W).pack(side=LEFT, padx=10, pady=5)
        
        value_label = Label(row, text="—", font=("Arial", 10, "bold"),
                          bg=self.colors['bg_input'], fg=self.colors['text_primary'],
                          anchor=E)
        value_label.pack(side=RIGHT, padx=10, pady=5)
        
        # Store reference to value label
        setattr(self, var_name, value_label)
        
    def add_log(self, log_type, message):
        """Add a log entry"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        self.log_text.config(state=NORMAL)
        self.log_text.insert(END, f"[{timestamp}] ", "timestamp")
        self.log_text.insert(END, f"[{log_type.upper()}] ", log_type)
        self.log_text.insert(END, f"{message}\n")
        self.log_text.see(END)
        self.log_text.config(state=DISABLED)
        
    def clear_logs(self):
        """Clear all logs"""
        self.log_text.config(state=NORMAL)
        self.log_text.delete(1.0, END)
        self.log_text.config(state=DISABLED)
        
    def update_status(self, status):
        """Update status badge"""
        status_map = {
            'connected': ('🟢 Connected', '#ecfdf5', '#065f46'),
            'active': ('🔵 Active', '#eff6ff', '#1e40af'),
            'navigating': ('🧭 Navigating', '#fef3c7', '#92400e'),
            'warning': ('⚠️ Warning', '#fef2f2', '#991b1b'),
            'disconnected': ('⚪ Disconnected', '#f3f4f6', '#6b7280'),
        }
        
        text, bg, fg = status_map.get(status, status_map['disconnected'])
        self.status_label.config(text=text, bg=bg, fg=fg)
        
    # ─── Control Methods ───
    
    def start_system(self):
        """Start SURDAS system"""
        if self.brain is None:
            self.add_log("info", "Initializing SURDAS brain...")
            
            try:
                self.brain = SurdasBrain()
                self.brain.headless = False
                
                # Start brain thread
                self.brain_thread = BrainThread(self.brain, self)
                self.brain_thread.start()
                
                # Update UI
                self.start_btn.config(state=DISABLED)
                self.stop_btn.config(state=NORMAL)
                self.nav_btn.config(state=NORMAL)
                self.ocr_btn.config(state=NORMAL)
                self.currency_btn.config(state=NORMAL)
                self.torch_btn.config(state=NORMAL)
                self.update_status("connected")
                
                self.add_log("success", "✅ System started successfully")
                self.start_time = time.time()
                
            except Exception as e:
                self.add_log("error", f"Failed to start: {str(e)}")
                
    def stop_system(self):
        """Stop SURDAS system"""
        if self.brain:
            self.add_log("info", "Stopping system...")
            self.brain.should_stop = True
            
            # Give thread time to stop
            if self.brain_thread:
                self.brain_thread.join(timeout=2)
                
            self.brain = None
            self.brain_thread = None
            
            # Update UI
            self.start_btn.config(state=NORMAL)
            self.stop_btn.config(state=DISABLED)
            self.nav_btn.config(state=DISABLED)
            self.ocr_btn.config(state=DISABLED)
            self.currency_btn.config(state=DISABLED)
            self.torch_btn.config(state=DISABLED)
            self.update_status("disconnected")
            
            self.add_log("info", "⏹️ System stopped")
            
    def set_mode(self, mode):
        """Set operating mode"""
        if self.brain:
            self.brain.mode = mode
            self.add_log("info", f"Mode changed to: {mode}")
            
    def toggle_torch(self):
        """Toggle flashlight"""
        if self.brain:
            self.brain.toggle_esp32_led(not self.brain.led_on)
            state = "ON" if self.brain.led_on else "OFF"
            self.add_log("info", f"Flashlight {state}")
            
    def update_display(self):
        """Update display with latest data"""
        if not self.update_running:
            return
            
        if self.brain:
            # Update video
            if hasattr(self.brain, 'latest_display_frame') and self.brain.latest_display_frame is not None:
                self.update_video(self.brain.latest_display_frame)
                
            # Update vision state
            self.mode_label.config(text=self.brain.mode, fg=self.colors['blue'])
            
            torch_text = "ON" if self.brain.led_on else "OFF"
            torch_color = self.colors['amber'] if self.brain.led_on else self.colors['gray']
            self.torch_label.config(text=torch_text, fg=torch_color)
            
            # Update obstacle info
            if hasattr(self.brain, 'latest_closest_obstacle') and self.brain.latest_closest_obstacle:
                self.obstacle_label.config(text=self.brain.latest_closest_obstacle[:30])
            else:
                self.obstacle_label.config(text="✅ Clear", fg=self.colors['green'])
                
            # Update wall detection
            if hasattr(self.brain, 'wall_detected'):
                wall_text = "YES" if self.brain.wall_detected else "NO"
                wall_color = self.colors['red'] if self.brain.wall_detected else self.colors['green']
                self.wall_label.config(text=wall_text, fg=wall_color)
                
            # Update detected objects
            if hasattr(self.brain, 'latest_detected_objects') and self.brain.latest_detected_objects:
                objects = list(set(self.brain.latest_detected_objects[:10]))
                self.objects_text.config(state=NORMAL)
                self.objects_text.delete(1.0, END)
                self.objects_text.insert(1.0, ", ".join(objects))
                self.objects_text.config(state=DISABLED)
                
                self.objects_count_label.config(text=str(len(set(self.brain.latest_detected_objects))))
            
            # Update navigation state
            if hasattr(self.brain, 'indoor_navigator') and self.brain.indoor_navigator:
                nav = self.brain.indoor_navigator
                
                state_colors = {
                    "IDLE": self.colors['gray'],
                    "NAVIGATING": self.colors['blue'],
                    "SAFETY_HOLD": self.colors['red'],
                    "APPROACHING": self.colors['green'],
                    "ARRIVED": '#059669'
                }
                
                self.nav_state_label.config(text=nav.state,
                                           fg=state_colors.get(nav.state, self.colors['gray']))
                self.nav_dest_label.config(text=nav.destination or "—")
                
                if hasattr(self.brain, 'indoor_perception'):
                    perc = self.brain.indoor_perception
                    if hasattr(perc, 'current_confidence'):
                        self.nav_conf_label.config(text=perc.current_confidence)
                    if hasattr(perc, 'safe_direction_count'):
                        self.nav_safe_label.config(text=str(perc.safe_direction_count))
            
            # Update uptime
            if self.start_time:
                uptime = int(time.time() - self.start_time)
                hours = uptime // 3600
                minutes = (uptime % 3600) // 60
                seconds = uptime % 60
                self.uptime_label.config(text=f"{hours:02d}:{minutes:02d}:{seconds:02d}")
                
            # Update status badge based on activity
            if self.brain.mode != "IDLE":
                if hasattr(self.brain, 'indoor_navigator') and self.brain.indoor_navigator.state == "NAVIGATING":
                    self.update_status("navigating")
                else:
                    self.update_status("active")
            else:
                self.update_status("connected")
                
        # Schedule next update (20 FPS)
        self.root.after(50, self.update_display)
        
    def update_video(self, frame):
        """Update video display"""
        try:
            # Convert BGR to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Resize to fit display (maintaining aspect ratio)
            height, width = rgb_frame.shape[:2]
            max_width = 640
            max_height = 480
            scale = min(max_width/width, max_height/height)
            new_width = int(width * scale)
            new_height = int(height * scale)
            
            resized = cv2.resize(rgb_frame, (new_width, new_height))
            
            # Convert to PhotoImage
            img = Image.fromarray(resized)
            photo = ImageTk.PhotoImage(image=img)
            
            # Update label
            self.video_label.config(image=photo, text="")
            self.video_label.image = photo  # Keep a reference
            
        except Exception as e:
            pass  # Silently ignore video update errors
            
    def on_closing(self):
        """Handle window close event"""
        self.update_running = False
        if self.brain:
            self.stop_system()
        self.root.destroy()


def main():
    """Main entry point"""
    root = Tk()
    app = SurdasGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
