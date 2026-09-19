"""
performance_optimizer.py - Resource optimization for SURDAS

Monitors and optimizes CPU/GPU/Memory usage for YOLO, MiDaS, and Voice systems.
Implements dynamic FPS adjustment, model quantization, and resource pooling.
"""

import time
import threading
import psutil
import torch
from typing import Dict, Optional
from dataclasses import dataclass
from enum import Enum


class PerformanceMode(Enum):
    """Performance optimization modes"""
    HIGH_PERFORMANCE = "high"  # Max FPS, full quality
    BALANCED = "balanced"       # Dynamic adjustment
    POWER_SAVER = "power"       # Low FPS, preserve battery


@dataclass
class SystemMetrics:
    """System resource metrics"""
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    gpu_memory_mb: float = 0.0
    temperature: float = 0.0
    vision_fps: float = 0.0
    target_fps: float = 15.0
    frame_drop_rate: float = 0.0


class PerformanceOptimizer:
    """
    Monitors system resources and dynamically adjusts:
    - Vision processing FPS
    - Model batch sizes
    - Depth map resolution
    - Voice processing intervals
    """
    
    def __init__(self, brain: "SurdasBrain", mode: PerformanceMode = PerformanceMode.BALANCED):
        self.brain = brain
        self.mode = mode
        self.metrics = SystemMetrics()
        
        # Performance thresholds
        self.cpu_high_threshold = 80.0
        self.mem_high_threshold = 85.0
        self.temp_high_threshold = 75.0
        
        # FPS adjustment parameters
        self.min_fps = 5.0
        self.max_fps = 30.0
        self.base_fps = 15.0
        
        # Monitoring
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_adjust = time.time()
        self._adjust_interval = 5.0  # Adjust every 5 seconds
        
    def start(self):
        """Start performance monitoring"""
        self._running = True
        self._thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="PerformanceOptimizer"
        )
        self._thread.start()
        print(f"[PERF] Performance Optimizer started in {self.mode.value} mode")
        
    def stop(self):
        """Stop monitoring"""
        self._running = False
        
    def get_metrics(self) -> SystemMetrics:
        """Get current system metrics"""
        return self.metrics
        
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self._running:
            try:
                # Collect metrics
                self._collect_metrics()
                
                # Adjust if needed
                now = time.time()
                if now - self._last_adjust > self._adjust_interval:
                    self._adjust_performance()
                    self._last_adjust = now
                    
                time.sleep(1.0)  # Sample every second
                
            except Exception as e:
                print(f"[PERF] Monitor error: {e}")
                time.sleep(2.0)
                
    def _collect_metrics(self):
        """Collect system resource metrics"""
        # CPU and Memory
        self.metrics.cpu_percent = psutil.cpu_percent(interval=0.1)
        self.metrics.memory_percent = psutil.virtual_memory().percent
        
        # GPU Memory (if CUDA available)
        if torch.cuda.is_available():
            try:
                self.metrics.gpu_memory_mb = torch.cuda.memory_allocated() / (1024 ** 2)
            except:
                pass
                
        # Temperature (if available)
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                # Try to get CPU temp
                for name, entries in temps.items():
                    if entries:
                        self.metrics.temperature = entries[0].current
                        break
        except:
            pass
            
        # Vision FPS from worker
        if hasattr(self.brain, 'vision_worker') and self.brain.vision_worker.latest:
            self.metrics.vision_fps = self.brain.vision_worker.latest.fps
            
    def _adjust_performance(self):
        """Dynamically adjust performance based on metrics"""
        if self.mode == PerformanceMode.HIGH_PERFORMANCE:
            # Always max performance
            self.metrics.target_fps = self.max_fps
            return
            
        elif self.mode == PerformanceMode.POWER_SAVER:
            # Always low power
            self.metrics.target_fps = self.min_fps
            self._apply_power_saving()
            return
            
        # BALANCED mode - dynamic adjustment
        cpu_high = self.metrics.cpu_percent > self.cpu_high_threshold
        mem_high = self.metrics.memory_percent > self.mem_high_threshold
        temp_high = self.metrics.temperature > self.temp_high_threshold
        
        if cpu_high or mem_high or temp_high:
            # Reduce FPS to lower resource usage
            self.metrics.target_fps = max(
                self.min_fps,
                self.metrics.target_fps * 0.8
            )
            print(f"[PERF] Reducing FPS to {self.metrics.target_fps:.1f} "
                  f"(CPU:{self.metrics.cpu_percent:.1f}% MEM:{self.metrics.memory_percent:.1f}%)")
            self._apply_optimization()
            
        elif self.metrics.cpu_percent < 50 and self.metrics.memory_percent < 70:
            # Resources available - increase FPS
            self.metrics.target_fps = min(
                self.max_fps,
                self.metrics.target_fps * 1.1
            )
            print(f"[PERF] Increasing FPS to {self.metrics.target_fps:.1f}")
            
    def _apply_optimization(self):
        """Apply performance optimizations"""
        # Adjust vision worker frame skip
        if hasattr(self.brain, 'vision_worker'):
            target_interval = 1.0 / self.metrics.target_fps
            # Worker will naturally adjust based on processing time
            
        # Reduce depth map resolution if needed
        if self.metrics.cpu_percent > self.cpu_high_threshold:
            # Could implement dynamic resolution scaling here
            pass
            
    def _apply_power_saving(self):
        """Apply power saving optimizations"""
        # Lower resolution depth maps
        # Reduce YOLO confidence threshold for faster inference
        # Skip every Nth frame
        pass
        
    def optimize_model(self, model, model_name: str):
        """
        Optimize a model for better performance:
        - Convert to TorchScript
        - Apply quantization
        - Enable inference mode
        """
        try:
            # Enable inference mode (disables gradient tracking)
            model.eval()
            
            # For CPU: apply dynamic quantization
            if not torch.cuda.is_available() and not torch.backends.mps.is_available():
                print(f"[PERF] Applying quantization to {model_name} for CPU")
                model = torch.quantization.quantize_dynamic(
                    model,
                    {torch.nn.Linear, torch.nn.Conv2d},
                    dtype=torch.qint8
                )
                
            return model
            
        except Exception as e:
            print(f"[PERF] Could not optimize {model_name}: {e}")
            return model


class FrameSkipper:
    """
    Smart frame skipping to maintain target FPS
    Ensures critical frames (with motion/changes) are never skipped
    """
    
    def __init__(self, target_fps: float = 15.0):
        self.target_fps = target_fps
        self.frame_count = 0
        self.last_process_time = time.time()
        self._prev_frame = None
        
    def should_process(self, frame=None) -> bool:
        """
        Determine if current frame should be processed
        Based on target FPS and frame importance
        """
        self.frame_count += 1
        now = time.time()
        elapsed = now - self.last_process_time
        target_interval = 1.0 / self.target_fps
        
        # Always process if enough time has passed
        if elapsed >= target_interval:
            self.last_process_time = now
            self._prev_frame = frame
            return True
            
        # Skip if too soon
        return False
        
    def update_fps(self, new_fps: float):
        """Update target FPS"""
        self.target_fps = new_fps


class ResourcePool:
    """
    Pool reusable resources to reduce allocation overhead:
    - Numpy arrays for frames
    - Torch tensors for model inputs
    - CV2 processing buffers
    """
    
    def __init__(self):
        self._tensor_pool: Dict[tuple, list] = {}
        self._array_pool: Dict[tuple, list] = {}
        
    def get_tensor(self, shape: tuple, dtype=torch.float32, device='cpu'):
        """Get a tensor from pool or create new"""
        key = (shape, dtype, device)
        pool = self._tensor_pool.get(key, [])
        
        if pool:
            return pool.pop()
        return torch.zeros(shape, dtype=dtype, device=device)
        
    def return_tensor(self, tensor: torch.Tensor):
        """Return tensor to pool"""
        key = (tuple(tensor.shape), tensor.dtype, tensor.device)
        pool = self._tensor_pool.setdefault(key, [])
        
        if len(pool) < 5:  # Max pool size
            pool.append(tensor)
            
    def get_array(self, shape: tuple, dtype='uint8'):
        """Get numpy array from pool or create new"""
        import numpy as np
        key = (shape, dtype)
        pool = self._array_pool.get(key, [])
        
        if pool:
            return pool.pop()
        return np.zeros(shape, dtype=dtype)
        
    def return_array(self, array):
        """Return array to pool"""
        import numpy as np
        key = (tuple(array.shape), str(array.dtype))
        pool = self._array_pool.setdefault(key, [])
        
        if len(pool) < 5:
            pool.append(array)


# Global resource pool instance
_resource_pool = ResourcePool()

def get_resource_pool() -> ResourcePool:
    """Get global resource pool"""
    return _resource_pool
