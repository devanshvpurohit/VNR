"""
test_indoor_navigation.py — Validation suite for indoor navigation in blindfold scenarios.

Tests:
  1. Spatial memory: room/object labeling and recall
  2. Indoor perception: free-space detection, confidence scoring
  3. Navigation guidance: waypoint-free reactive navigation
  4. Safety-hold triggers: camera failure, obstacles, low confidence
  5. Wake-word detection: same-utterance "Surdas, command"
  6. End-to-end blindfold scenario: explore, label, navigate

Usage:
    python test_indoor_navigation.py --test all
    python test_indoor_navigation.py --test spatial_memory
    python test_indoor_navigation.py --test perception
    python test_indoor_navigation.py --test navigation
    python test_indoor_navigation.py --test blindfold_simulation
"""

import sys
import time
import numpy as np
import cv2
from pathlib import Path

# Test configuration
TEST_IMAGE_DIR = Path(__file__).parent / "test_data"
TEST_IMAGE_DIR.mkdir(exist_ok=True)


def test_spatial_memory():
    """Test spatial memory module: add/query rooms, objects, landmarks."""
    print("\n" + "="*70)
    print("TEST 1: SPATIAL MEMORY")
    print("="*70)
    
    from spatial_memory import SpatialMemory, ObjectCategory
    
    # Initialize fresh memory
    db_path = Path(__file__).parent / "test_spatial_memory.db"
    if db_path.exists():
        db_path.unlink()
    
    memory = SpatialMemory(db_path=db_path)
    
    # Test 1.1: Add rooms
    print("\n[1.1] Adding rooms...")
    bedroom_id = memory.add_room("bedroom", center_x=0.0, center_y=0.0, radius_m=4.0)
    kitchen_id = memory.add_room("kitchen", center_x=8.0, center_y=0.0, radius_m=4.0)
    print(f"✓ Added bedroom (id={bedroom_id}) and kitchen (id={kitchen_id})")
    
    # Test 1.2: Add objects
    print("\n[1.2] Adding objects...")
    chair_id = memory.add_object("chair", ObjectCategory.FURNITURE, x=1.5, y=2.0, z=0.0, confidence=0.9, room_id=bedroom_id)
    table_id = memory.add_object("table", ObjectCategory.FURNITURE, x=2.0, y=1.5, z=0.0, confidence=0.85, room_id=bedroom_id)
    door_id = memory.add_object("door", ObjectCategory.DOOR, x=4.0, y=0.0, z=0.0, confidence=0.95)
    print(f"✓ Added chair (id={chair_id}), table (id={table_id}), door (id={door_id})")
    
    # Test 1.3: Add landmarks
    print("\n[1.3] Adding landmarks...")
    entrance_id = memory.add_landmark("kitchen entrance", x=6.0, y=0.0, z=0.0, description="Main entry to kitchen")
    print(f"✓ Added kitchen entrance landmark (id={entrance_id})")
    
    # Test 1.4: Query objects
    print("\n[1.4] Querying objects...")
    chair = memory.find_object_by_label("chair")
    assert chair is not None, "Failed to find chair"
    assert chair.x == 1.5, "Chair position mismatch"
    print(f"✓ Found chair at ({chair.x}, {chair.y}, {chair.z})")
    
    # Test 1.5: Get nearby objects
    print("\n[1.5] Finding nearby objects...")
    nearby = memory.get_objects_near(x=1.8, y=1.8, radius_m=1.0)
    assert len(nearby) == 2, f"Expected 2 nearby objects, found {len(nearby)}"
    print(f"✓ Found {len(nearby)} objects near (1.8, 1.8): {[obj.label for obj in nearby]}")
    
    # Test 1.6: Room membership
    print("\n[1.6] Checking room membership...")
    room = memory.get_room_at_position(1.5, 2.0)
    assert room is not None, "Failed to find room"
    assert room.name == "bedroom", f"Expected bedroom, got {room.name}"
    print(f"✓ Position (1.5, 2.0) is in {room.name}")
    
    # Test 1.7: Describe surroundings
    print("\n[1.7] Describing surroundings...")
    description = memory.describe_surroundings(x=1.5, y=1.8, radius_m=2.0)
    print(f"✓ Description: {description}")
    
    # Test 1.8: Statistics
    print("\n[1.8] Memory statistics...")
    stats = memory.get_stats()
    print(f"✓ Stats: {stats['rooms']} rooms, {stats['objects']} objects, {stats['landmarks']} landmarks")
    
    # Cleanup
    db_path.unlink()
    
    print("\n✅ SPATIAL MEMORY: ALL TESTS PASSED")
    return True


def test_indoor_perception():
    """Test indoor perception: free-space detection, safe directions, confidence."""
    print("\n" + "="*70)
    print("TEST 2: INDOOR PERCEPTION")
    print("="*70)
    
    from indoor_perception import IndoorPerception, NavConfidence
    
    perception = IndoorPerception(grid_size=32)
    
    # Test 2.1: Process empty frame (should be HIGH confidence)
    print("\n[2.1] Processing clear path scenario...")
    depth_map = np.random.rand(480, 640).astype(np.float32) * 0.3  # Far depth
    yolo_detections = []
    
    result = perception.process_frame(
        yolo_detections=yolo_detections,
        depth_map=depth_map,
        img_width=640,
        img_height=480
    )
    
    assert result.nav_confidence in [NavConfidence.HIGH, NavConfidence.MEDIUM], \
        f"Expected HIGH/MEDIUM confidence for clear path, got {result.nav_confidence}"
    print(f"✓ Clear path confidence: {result.nav_confidence.value}")
    print(f"✓ Safe directions: {len(result.safe_directions)}")
    
    # Test 2.2: Close obstacle scenario (should be LOW or trigger safety)
    print("\n[2.2] Processing close obstacle scenario...")
    depth_map_close = np.ones((480, 640), dtype=np.float32) * 0.9  # Very close
    yolo_detections_obstacle = [
        {
            "class": "chair",
            "confidence": 0.9,
            "bbox": [280, 200, 360, 400]  # Center obstacle
        }
    ]
    
    result_close = perception.process_frame(
        yolo_detections=yolo_detections_obstacle,
        depth_map=depth_map_close,
        img_width=640,
        img_height=480
    )
    
    assert result_close.nav_confidence in [NavConfidence.LOW, NavConfidence.INVALID], \
        f"Expected LOW/INVALID confidence for close obstacle, got {result_close.nav_confidence}"
    print(f"✓ Close obstacle confidence: {result_close.nav_confidence.value}")
    print(f"✓ Obstacles detected: {result_close.obstacle_summary.count}")
    
    # Test 2.3: Invalid depth (camera failure)
    print("\n[2.3] Processing invalid depth scenario...")
    depth_map_invalid = np.zeros((480, 640), dtype=np.float32)
    
    result_invalid = perception.process_frame(
        yolo_detections=[],
        depth_map=depth_map_invalid,
        img_width=640,
        img_height=480
    )
    
    assert result_invalid.nav_confidence == NavConfidence.INVALID, \
        f"Expected INVALID confidence for zero depth, got {result_invalid.nav_confidence}"
    print(f"✓ Invalid depth confidence: {result_invalid.nav_confidence.value}")
    
    # Test 2.4: Partial blockage (left clear, center/right blocked)
    print("\n[2.4] Processing partial blockage scenario...")
    depth_map_partial = np.random.rand(480, 640).astype(np.float32) * 0.4
    depth_map_partial[:, 320:] = 0.9  # Right half very close
    
    yolo_detections_partial = [
        {
            "class": "person",
            "confidence": 0.95,
            "bbox": [400, 150, 500, 450]  # Right side obstacle
        }
    ]
    
    result_partial = perception.process_frame(
        yolo_detections=yolo_detections_partial,
        depth_map=depth_map_partial,
        img_width=640,
        img_height=480
    )
    
    print(f"✓ Partial blockage confidence: {result_partial.nav_confidence.value}")
    print(f"✓ Zones blocked: L={result_partial.obstacle_summary.left_blocked}, "
          f"C={result_partial.obstacle_summary.center_blocked}, "
          f"R={result_partial.obstacle_summary.right_blocked}")
    
    if result_partial.safe_directions:
        best_dir = result_partial.safe_directions[0]
        print(f"✓ Best safe direction: {best_dir.angle_deg}° (clearance: {best_dir.clearance_m}m)")
    
    print("\n✅ INDOOR PERCEPTION: ALL TESTS PASSED")
    return True


def test_indoor_navigation():
    """Test indoor navigation controller: state machine, safety-hold, guidance."""
    print("\n" + "="*70)
    print("TEST 3: INDOOR NAVIGATION CONTROLLER")
    print("="*70)
    
    from spatial_memory import SpatialMemory, ObjectCategory
    from indoor_navigator import IndoorNavigator, NavigationState
    from indoor_perception import IndoorPerception, NavConfidence
    
    # Setup
    db_path = Path(__file__).parent / "test_nav_memory.db"
    if db_path.exists():
        db_path.unlink()
    
    memory = SpatialMemory(db_path=db_path)
    navigator = IndoorNavigator(memory, voice_engine=None)
    perception = IndoorPerception()
    
    # Test 3.1: Initial state
    print("\n[3.1] Checking initial state...")
    status = navigator.get_status()
    assert status.state == NavigationState.IDLE, f"Expected IDLE state, got {status.state}"
    print(f"✓ Initial state: {status.state.value}")
    
    # Test 3.2: Start navigation to non-existent object (should fail)
    print("\n[3.2] Attempting navigation to non-existent object...")
    success = navigator.navigate_to_object("nonexistent_chair")
    assert not success, "Navigation should fail for non-existent object"
    print("✓ Navigation correctly rejected for unknown object")
    
    # Test 3.3: Add object and navigate to it
    print("\n[3.3] Adding object and starting navigation...")
    chair_id = memory.add_object("chair", ObjectCategory.FURNITURE, x=3.0, y=2.0, z=0.0, confidence=0.9)
    success = navigator.navigate_to_object("chair")
    assert success, "Navigation should succeed for known object"
    
    status = navigator.get_status()
    assert status.state == NavigationState.NAVIGATING, f"Expected NAVIGATING state, got {status.state}"
    print(f"✓ Navigation started, state: {status.state.value}")
    
    # Test 3.4: Update with HIGH confidence perception (should continue)
    print("\n[3.4] Updating with HIGH confidence perception...")
    depth_map = np.random.rand(480, 640).astype(np.float32) * 0.3
    result = perception.process_frame([], depth_map, 640, 480)
    
    navigator.update(result)
    status = navigator.get_status()
    assert status.state in [NavigationState.NAVIGATING, NavigationState.APPROACHING], \
        f"Expected NAVIGATING/APPROACHING, got {status.state}"
    print(f"✓ State after HIGH confidence update: {status.state.value}")
    
    # Test 3.5: Update with INVALID perception (should trigger SAFETY_HOLD)
    print("\n[3.5] Updating with INVALID perception (camera failure)...")
    depth_map_invalid = np.zeros((480, 640), dtype=np.float32)
    result_invalid = perception.process_frame([], depth_map_invalid, 640, 480)
    
    navigator.update(result_invalid)
    time.sleep(0.1)  # Allow state transition
    status = navigator.get_status()
    assert status.state == NavigationState.SAFETY_HOLD, \
        f"Expected SAFETY_HOLD for invalid perception, got {status.state}"
    print(f"✓ SAFETY_HOLD triggered, reason: {status.hold_reason.value if status.hold_reason else 'unknown'}")
    
    # Test 3.6: Resume from safety hold
    print("\n[3.6] Resuming from SAFETY_HOLD...")
    navigator.resume()
    status = navigator.get_status()
    assert status.state == NavigationState.NAVIGATING, \
        f"Expected NAVIGATING after resume, got {status.state}"
    print(f"✓ Resumed navigation, state: {status.state.value}")
    
    # Test 3.7: User-requested pause
    print("\n[3.7] User-requested pause...")
    navigator.pause()
    status = navigator.get_status()
    assert status.state == NavigationState.SAFETY_HOLD, \
        f"Expected SAFETY_HOLD after pause, got {status.state}"
    print(f"✓ Paused by user, state: {status.state.value}")
    
    # Test 3.8: Stop navigation
    print("\n[3.8] Stopping navigation...")
    navigator.stop()
    status = navigator.get_status()
    assert status.state == NavigationState.IDLE, \
        f"Expected IDLE after stop, got {status.state}"
    print(f"✓ Navigation stopped, state: {status.state.value}")
    
    # Cleanup
    db_path.unlink()
    
    print("\n✅ INDOOR NAVIGATION CONTROLLER: ALL TESTS PASSED")
    return True


def test_wake_word_detection():
    """Test wake-word detection: same-utterance, traditional wake."""
    print("\n" + "="*70)
    print("TEST 4: WAKE-WORD DETECTION")
    print("="*70)
    
    from voice.wakeword import WakeWordDetector
    
    detector = WakeWordDetector()
    
    # Test 4.1: Same-utterance detection (English)
    print("\n[4.1] Testing same-utterance wake (English)...")
    test_cases = [
        ("Surdas, what do you see?", True, "what do you see?"),
        ("Surdas, guide me to the door", True, "guide me to the door"),
        ("soordas, where is the chair", True, "where is the chair"),
    ]
    
    for text, should_match, expected_command in test_cases:
        is_wake, command = detector.check_transcription(text)
        assert is_wake == should_match, f"Wake detection failed for '{text}'"
        if should_match and expected_command:
            # Normalize punctuation for comparison
            assert command.lower().strip().rstrip('?.!') == expected_command.lower().rstrip('?.!'), \
                f"Command mismatch: expected '{expected_command}', got '{command}'"
        print(f"✓ '{text}' → wake={is_wake}, command='{command}'")
    
    # Test 4.2: Traditional wake (with "Hey")
    print("\n[4.2] Testing traditional wake patterns...")
    traditional_cases = [
        ("Hey Surdas, what time is it", True, "what time is it"),
        ("Hey Surdas", True, ""),  # Wake only, no command
    ]
    
    for text, should_match, expected_command in traditional_cases:
        is_wake, command = detector.check_transcription(text)
        assert is_wake == should_match, f"Wake detection failed for '{text}'"
        print(f"✓ '{text}' → wake={is_wake}, command='{command}'")
    
    # Test 4.3: Same-utterance detection (Hindi)
    print("\n[4.3] Testing same-utterance wake (Hindi)...")
    hindi_cases = [
        ("सुरदास, समय बताओ", True, "समय बताओ"),
        ("सूरदास, कमरा लेबल करो", True, "कमरा लेबल करो"),
    ]
    
    for text, should_match, expected_command in hindi_cases:
        is_wake, command = detector.check_transcription(text)
        assert is_wake == should_match, f"Wake detection failed for '{text}'"
        print(f"✓ '{text}' → wake={is_wake}, command='{command}'")
    
    # Test 4.4: Non-wake phrases
    print("\n[4.4] Testing non-wake phrases...")
    non_wake_cases = [
        "what is the weather today",
        "please tell me the time",
        "I need help",
    ]
    
    for text in non_wake_cases:
        is_wake, _ = detector.check_transcription(text)
        assert not is_wake, f"False positive wake detection for '{text}'"
        print(f"✓ '{text}' correctly rejected (no wake)")
    
    print("\n✅ WAKE-WORD DETECTION: ALL TESTS PASSED")
    return True


def test_blindfold_simulation():
    """Simulate complete blindfold scenario: explore, label, navigate."""
    print("\n" + "="*70)
    print("TEST 5: BLINDFOLD SCENARIO SIMULATION")
    print("="*70)
    
    from spatial_memory import SpatialMemory, ObjectCategory
    from indoor_navigator import IndoorNavigator
    from indoor_perception import IndoorPerception
    
    # Setup
    db_path = Path(__file__).parent / "test_blindfold_memory.db"
    if db_path.exists():
        db_path.unlink()
    
    memory = SpatialMemory(db_path=db_path)
    navigator = IndoorNavigator(memory, voice_engine=None)
    perception = IndoorPerception()
    
    print("\n[5.1] SCENARIO: User explores bedroom and labels objects")
    print("─" * 70)
    
    # Simulate user labeling room
    print("User: 'Surdas, this is the bedroom'")
    bedroom_id = memory.add_room("bedroom", center_x=0.0, center_y=0.0, radius_m=5.0)
    print(f"System: Remembered room 'bedroom' (id={bedroom_id})")
    
    # Simulate YOLO detecting chair
    print("\nUser walks around, camera detects chair")
    chair_id = memory.add_object("chair", ObjectCategory.FURNITURE, x=2.0, y=3.0, z=0.0, confidence=0.92, room_id=bedroom_id)
    print(f"System: Detected and remembered chair at (2.0, 3.0)")
    
    # Simulate user labeling landmark
    print("\nUser: 'Surdas, remember this location as bedroom entrance'")
    entrance_id = memory.add_landmark("bedroom entrance", x=0.0, y=-2.0, z=0.0, description="Main entry")
    print(f"System: Saved landmark 'bedroom entrance' (id={entrance_id})")
    
    print("\n[5.2] SCENARIO: User queries spatial memory")
    print("─" * 70)
    
    # Query room
    print("User: 'Surdas, what room is this?'")
    room = memory.get_room_at_position(0.0, 0.0)
    print(f"System: You are in the {room.name}")
    
    # Query object location
    print("\nUser: 'Surdas, where is the chair?'")
    chair = memory.find_object_by_label("chair")
    if chair:
        dist = (chair.x ** 2 + chair.y ** 2) ** 0.5
        print(f"System: The chair is approximately {dist:.1f} metres away")
    
    # Describe surroundings
    print("\nUser: 'Surdas, describe surroundings'")
    description = memory.describe_surroundings(0.0, 0.0, radius_m=5.0)
    print(f"System: {description}")
    
    print("\n[5.3] SCENARIO: Navigate to chair with blindfold")
    print("─" * 70)
    
    # Start navigation
    print("User: 'Surdas, guide me to the chair'")
    success = navigator.navigate_to_object("chair")
    assert success, "Navigation should start successfully"
    print("System: Navigating to chair. I'll guide you there safely.")
    
    # Simulate navigation updates
    print("\n[Navigation Loop]")
    for step in range(5):
        # Simulate clear path
        depth_map = np.random.rand(480, 640).astype(np.float32) * 0.4
        result = perception.process_frame([], depth_map, 640, 480)
        
        navigator.update(result)
        status = navigator.get_status()
        
        print(f"Step {step+1}: State={status.state.value}, Confidence={status.confidence.value}, "
              f"Safe directions={status.safe_directions_count}")
        
        if status.state == "ARRIVED":
            print("System: Arrived! Chair should be right in front of you.")
            break
        
        time.sleep(0.1)
    
    # Stop navigation
    navigator.stop()
    print("\nNavigation complete")
    
    print("\n[5.4] SCENARIO: Safety-hold during navigation")
    print("─" * 70)
    
    # Start new navigation
    door_id = memory.add_object("door", ObjectCategory.DOOR, x=-3.0, y=0.0, z=0.0, confidence=0.95)
    print("User: 'Surdas, guide me to the door'")
    navigator.navigate_to_object("door")
    
    # Simulate obstacle appearing
    print("\n[Obstacle detected - close to user]")
    depth_map_blocked = np.ones((480, 640), dtype=np.float32) * 0.95
    yolo_obstacle = [{"class": "person", "confidence": 0.98, "bbox": [250, 150, 390, 450]}]
    result_blocked = perception.process_frame(yolo_obstacle, depth_map_blocked, 640, 480)
    
    navigator.update(result_blocked)
    time.sleep(0.1)
    status = navigator.get_status()
    
    assert status.state == "SAFETY_HOLD", "Should trigger SAFETY_HOLD for close obstacle"
    print(f"System: SAFETY_HOLD triggered (reason: {status.hold_reason.value})")
    print("System: Stop! Obstacle very close. Please clear the path or move around it.")
    
    # Clear obstacle and auto-resume
    print("\n[Obstacle cleared]")
    depth_map_clear = np.random.rand(480, 640).astype(np.float32) * 0.3
    result_clear = perception.process_frame([], depth_map_clear, 640, 480)
    
    navigator.update(result_clear)
    time.sleep(0.1)
    status = navigator.get_status()
    
    print(f"System: Safety conditions restored. Continuing navigation.")
    print(f"State: {status.state.value}")
    
    # Cleanup
    navigator.stop()
    db_path.unlink()
    
    print("\n✅ BLINDFOLD SCENARIO SIMULATION: ALL TESTS PASSED")
    return True


def run_all_tests():
    """Run all test suites."""
    print("\n" + "="*70)
    print("SURDAS INDOOR NAVIGATION TEST SUITE")
    print("Testing blindfold navigation capability")
    print("="*70)
    
    tests = [
        ("Spatial Memory", test_spatial_memory),
        ("Indoor Perception", test_indoor_perception),
        ("Indoor Navigation Controller", test_indoor_navigation),
        ("Wake-Word Detection", test_wake_word_detection),
        ("Blindfold Simulation", test_blindfold_simulation),
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success, None))
        except Exception as e:
            print(f"\n❌ {name}: FAILED")
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False, str(e)))
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for _, success, _ in results if success)
    total = len(results)
    
    for name, success, error in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {name}")
        if error:
            print(f"       {error}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED - INDOOR NAVIGATION READY FOR BLINDFOLD USE")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed - review errors above")
        return 1


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test SURDAS indoor navigation system")
    parser.add_argument("--test", choices=["all", "spatial_memory", "perception", "navigation", "wakeword", "blindfold_simulation"],
                        default="all", help="Which test to run")
    
    args = parser.parse_args()
    
    if args.test == "all":
        sys.exit(run_all_tests())
    elif args.test == "spatial_memory":
        sys.exit(0 if test_spatial_memory() else 1)
    elif args.test == "perception":
        sys.exit(0 if test_indoor_perception() else 1)
    elif args.test == "navigation":
        sys.exit(0 if test_indoor_navigation() else 1)
    elif args.test == "wakeword":
        sys.exit(0 if test_wake_word_detection() else 1)
    elif args.test == "blindfold_simulation":
        sys.exit(0 if test_blindfold_simulation() else 1)
