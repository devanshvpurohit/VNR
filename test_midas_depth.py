"""
test_midas_depth.py — Test MiDaS depth estimation functionality

This script captures a frame and tests depth estimation to verify MiDaS is working properly.
"""
import cv2
import torch
import numpy as np
import sys

print("=" * 70)
print("MiDaS Depth Estimation Test")
print("=" * 70)

# Setup device
DEVICE = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
print(f"Device: {DEVICE}")

# Load MiDaS
print("\n[1/4] Loading MiDaS model...")
try:
    midas = torch.hub.load("intel-isl/MiDaS", "MiDaS_small", trust_repo=True)
    midas.to(DEVICE)
    midas.eval()
    print("✅ MiDaS model loaded successfully")
except Exception as e:
    print(f"❌ Failed to load MiDaS: {e}")
    sys.exit(1)

# Load transforms
print("\n[2/4] Loading MiDaS transforms...")
try:
    midas_transforms = torch.hub.load("intel-isl/MiDaS", "transforms", trust_repo=True)
    transform = midas_transforms.small_transform
    print("✅ MiDaS transforms loaded successfully")
except Exception as e:
    print(f"❌ Failed to load transforms: {e}")
    sys.exit(1)

# Capture frame from webcam
print("\n[3/4] Creating test frame...")
try:
    # Create a synthetic test frame (gradient pattern)
    h, w = 480, 640
    frame = np.zeros((h, w, 3), dtype=np.uint8)
    
    # Create gradient pattern (simulates depth variation)
    for y in range(h):
        for x in range(w):
            # Horizontal gradient (left=dark, right=bright)
            frame[y, x] = [int(255 * x / w)] * 3
    
    # Add some shapes to test
    cv2.rectangle(frame, (100, 100), (200, 200), (255, 0, 0), -1)  # Blue square
    cv2.circle(frame, (400, 240), 50, (0, 255, 0), -1)  # Green circle
    
    print(f"✅ Test frame created: {w}x{h}")
except Exception as e:
    print(f"❌ Failed to create test frame: {e}")
    sys.exit(1)

# Test depth estimation
print("\n[4/4] Testing depth estimation...")
try:
    # Prepare input
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    input_tensor = transform(rgb).to(DEVICE)
    
    print(f"  Input tensor shape: {input_tensor.shape}")
    print(f"  Input tensor dtype: {input_tensor.dtype}")
    print(f"  Input tensor device: {input_tensor.device}")
    
    # Run inference
    with torch.no_grad():
        depth = midas(input_tensor)
        print(f"  Raw depth shape: {depth.shape}")
        print(f"  Raw depth dtype: {depth.dtype}")
        
        # Interpolate to original size
        depth = torch.nn.functional.interpolate(
            depth.unsqueeze(1),
            size=frame.shape[:2],
            mode="bicubic",
            align_corners=False
        ).squeeze()
        
        print(f"  Interpolated depth shape: {depth.shape}")
    
    # Convert to numpy
    depth_np = depth.cpu().numpy()
    print(f"  NumPy depth shape: {depth_np.shape}")
    print(f"  NumPy depth dtype: {depth_np.dtype}")
    print(f"  Depth range: [{depth_np.min():.2f}, {depth_np.max():.2f}]")
    print(f"  Depth mean: {depth_np.mean():.2f}")
    print(f"  Depth std: {depth_np.std():.2f}")
    
    # Check for valid depth values
    if depth_np.size == 0:
        print("❌ Depth map is empty")
        sys.exit(1)
    
    if np.isnan(depth_np).any():
        print("⚠️  Warning: Depth map contains NaN values")
        nan_count = np.isnan(depth_np).sum()
        print(f"  NaN count: {nan_count} / {depth_np.size} ({100*nan_count/depth_np.size:.2f}%)")
    
    if np.isinf(depth_np).any():
        print("⚠️  Warning: Depth map contains Inf values")
        inf_count = np.isinf(depth_np).sum()
        print(f"  Inf count: {inf_count} / {depth_np.size} ({100*inf_count/depth_np.size:.2f}%)")
    
    # Create visualization
    depth_vis = cv2.normalize(depth_np, None, 0, 255, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_8U)
    depth_colormap = cv2.applyColorMap(depth_vis, cv2.COLORMAP_INFERNO)
    
    # Sample depth values from different regions
    print("\n  Depth sampling (center, left, right):")
    center_x, center_y = w // 2, h // 2
    left_x, left_y = w // 4, h // 2
    right_x, right_y = 3 * w // 4, h // 2
    
    print(f"    Center ({center_x}, {center_y}): {depth_np[center_y, center_x]:.2f}")
    print(f"    Left   ({left_x}, {left_y}): {depth_np[left_y, left_x]:.2f}")
    print(f"    Right  ({right_x}, {right_y}): {depth_np[right_y, right_x]:.2f}")
    
    # Save output
    output_path = "test_midas_output.jpg"
    
    # Create side-by-side comparison
    combined = np.hstack([frame, depth_colormap])
    cv2.imwrite(output_path, combined)
    print(f"\n✅ Depth estimation successful")
    print(f"  Output saved to: {output_path}")
    
    # Test indoor perception compatibility
    print("\n[BONUS] Testing indoor perception compatibility...")
    from indoor_perception import IndoorPerception
    
    perception = IndoorPerception(grid_size=32)
    result = perception.process_frame(
        yolo_detections=[],
        depth_map=depth_np,
        img_width=w,
        img_height=h
    )
    
    print(f"✅ Indoor perception processed successfully")
    print(f"  Navigation confidence: {result.nav_confidence.value}")
    print(f"  Safe directions: {len(result.safe_directions)}")
    print(f"  Obstacle count: {result.obstacle_summary.count}")
    
except Exception as e:
    print(f"❌ Depth estimation failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 70)
print("✅ ALL TESTS PASSED - MiDaS is working correctly")
print("=" * 70)
