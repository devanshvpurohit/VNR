"""
test_navigation_depth.py — Test complete navigation with depth estimation

This verifies the full pipeline:
1. MiDaS depth estimation
2. Depth classification (fixed and adaptive)
3. Indoor perception integration
4. Navigation guidance
"""
import cv2
import torch
import numpy as np
import sys

print("=" * 70)
print("NAVIGATION DEPTH PIPELINE TEST")
print("=" * 70)

# Import configuration
from config import *

# Device setup
DEVICE = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
print(f"\nDevice: {DEVICE}")
print(f"Adaptive normalization: {DEPTH_ADAPTIVE_NORMALIZATION}")
print(f"Fixed thresholds: VERY_CLOSE={DEPTH_VERY_CLOSE_THRESHOLD}, CLOSE={DEPTH_CLOSE_THRESHOLD}, MEDIUM={DEPTH_MEDIUM_THRESHOLD}")

# Load models
print("\n[1/5] Loading models...")
try:
    # MiDaS
    midas = torch.hub.load("intel-isl/MiDaS", "MiDaS_small", trust_repo=True)
    midas.to(DEVICE)
    midas.eval()
    
    midas_transforms = torch.hub.load("intel-isl/MiDaS", "transforms", trust_repo=True)
    transform = midas_transforms.small_transform
    
    # YOLO
    from ultralytics import YOLO
    yolo = YOLO("yolov8n.pt")
    
    print("✅ Models loaded")
except Exception as e:
    print(f"❌ Model loading failed: {e}")
    sys.exit(1)

# Create test frame
print("\n[2/5] Creating test scene...")
h, w = 480, 640
frame = np.zeros((h, w, 3), dtype=np.uint8)

# Add some objects at different depths (simulate with brightness)
cv2.rectangle(frame, (50, 150), (150, 350), (200, 200, 200), -1)  # Far left - medium brightness
cv2.rectangle(frame, (250, 200), (390, 400), (100, 100, 100), -1)  # Center - dark (far)
cv2.circle(frame, (500, 240), 60, (255, 255, 255), -1)  # Right - bright (close)

print("✅ Test scene created")

# Run depth estimation
print("\n[3/5] Running MiDaS depth estimation...")
try:
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    input_tensor = transform(rgb).to(DEVICE)
    
    with torch.no_grad():
        depth = midas(input_tensor)
        depth = torch.nn.functional.interpolate(
            depth.unsqueeze(1),
            size=(h, w),
            mode="bicubic",
            align_corners=False
        ).squeeze()
    
    depth_np = depth.cpu().numpy()
    
    print(f"✅ Depth computed: range [{depth_np.min():.2f}, {depth_np.max():.2f}], mean {depth_np.mean():.2f}")
except Exception as e:
    print(f"❌ Depth estimation failed: {e}")
    sys.exit(1)

# Run YOLO
print("\n[4/5] Running YOLO object detection...")
try:
    results = yolo(frame, conf=0.25, verbose=False)[0]
    yolo_detections = []
    
    for box in results.boxes:
        cls_id = int(box.cls[0])
        conf = float(box.conf[0])
        label = yolo.names[cls_id]
        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
        
        yolo_detections.append({
            "class": label,
            "confidence": conf,
            "bbox": [x1, y1, x2, y2]
        })
    
    print(f"✅ YOLO detected {len(yolo_detections)} objects")
except Exception as e:
    print(f"❌ YOLO detection failed: {e}")
    sys.exit(1)

# Test depth classification
print("\n[5/5] Testing depth classification...")

# Sample three regions
regions = [
    ("Left", 100, 250),
    ("Center", 320, 300),
    ("Right", 500, 240)
]

print("\nFixed threshold classification:")
for name, x, y in regions:
    depth_val = depth_np[y, x]
    proximity = classify_depth_proximity(depth_val)
    proximity_desc = get_proximity_description(proximity, "en")
    print(f"  {name} ({x},{y}): depth={depth_val:.2f} → {proximity} ({proximity_desc})")

print("\nAdaptive threshold classification:")
for name, x, y in regions:
    depth_val = depth_np[y, x]
    proximity = classify_depth_proximity_adaptive(depth_val, depth_np)
    proximity_desc = get_proximity_description(proximity, "en")
    print(f"  {name} ({x},{y}): depth={depth_val:.2f} → {proximity} ({proximity_desc})")

# Test indoor perception
print("\n[BONUS] Testing indoor perception integration...")
try:
    from indoor_perception import IndoorPerception
    
    perception = IndoorPerception(grid_size=32)
    result = perception.process_frame(
        yolo_detections=yolo_detections,
        depth_map=depth_np,
        img_width=w,
        img_height=h
    )
    
    print(f"✅ Indoor perception processed")
    print(f"  Navigation confidence: {result.nav_confidence.value}")
    print(f"  Safe directions: {len(result.safe_directions)}")
    if result.safe_directions:
        best = result.safe_directions[0]
        print(f"  Best direction: {best.angle_deg}° (clearance: {best.clearance_m}m, confidence: {best.confidence.value})")
    print(f"  Obstacles: {result.obstacle_summary.count}")
    print(f"  Zones: L={result.obstacle_summary.left_blocked}, C={result.obstacle_summary.center_blocked}, R={result.obstacle_summary.right_blocked}")
    
except Exception as e:
    print(f"❌ Indoor perception failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Create visualization
depth_vis = cv2.normalize(depth_np, None, 0, 255, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_8U)
depth_colormap = cv2.applyColorMap(depth_vis, cv2.COLORMAP_INFERNO)

# Mark sample points
for name, x, y in regions:
    cv2.circle(frame, (x, y), 5, (0, 255, 0), -1)
    cv2.circle(depth_colormap, (x, y), 5, (0, 255, 0), -1)

# Save output
combined = np.hstack([frame, depth_colormap])
cv2.imwrite("test_navigation_depth_output.jpg", combined)

print("\n" + "=" * 70)
print("✅ ALL TESTS PASSED - NAVIGATION DEPTH PIPELINE WORKING")
print("Output saved to: test_navigation_depth_output.jpg")
print("=" * 70)
