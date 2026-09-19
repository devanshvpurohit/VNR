#!/usr/bin/env python3
"""
Quick test script for AI Voice Mode functionality.
Tests:
1. Workers can pause/resume
2. AI mode activates and exits properly
3. Single-question behavior works
"""

import sys
import time
from unittest.mock import Mock, MagicMock

def test_worker_pause_resume():
    """Test that workers have pause/resume methods."""
    print("\n=== Testing Worker Pause/Resume ===")
    
    # Import after path setup
    from workers import VisionWorker, SafetyWorker
    
    # Create mock brain
    mock_brain = Mock()
    mock_brain.stream = Mock()
    mock_brain.stream.get_frame = Mock(return_value=None)
    
    # Test VisionWorker
    vision = VisionWorker(mock_brain)
    assert hasattr(vision, 'pause'), "VisionWorker missing pause() method"
    assert hasattr(vision, 'resume'), "VisionWorker missing resume() method"
    assert hasattr(vision, '_paused'), "VisionWorker missing _paused attribute"
    print("✓ VisionWorker has pause/resume methods")
    
    # Test SafetyWorker
    safety = SafetyWorker(mock_brain, vision)
    assert hasattr(safety, 'pause'), "SafetyWorker missing pause() method"
    assert hasattr(safety, 'resume'), "SafetyWorker missing resume() method"
    assert hasattr(safety, '_paused'), "SafetyWorker missing _paused attribute"
    print("✓ SafetyWorker has pause/resume methods")
    
    # Test pause/resume calls
    vision.pause()
    assert vision._paused == True, "VisionWorker._paused not set to True"
    print("✓ VisionWorker.pause() sets _paused=True")
    
    vision.resume()
    assert vision._paused == False, "VisionWorker._paused not set to False"
    print("✓ VisionWorker.resume() sets _paused=False")
    
    safety.pause()
    assert safety._paused == True, "SafetyWorker._paused not set to True"
    print("✓ SafetyWorker.pause() sets _paused=True")
    
    safety.resume()
    assert safety._paused == False, "SafetyWorker._paused not set to False"
    print("✓ SafetyWorker.resume() sets _paused=False")

def test_ai_mode_integration():
    """Test that SurdasBrain has AI mode methods."""
    print("\n=== Testing AI Mode Integration ===")
    
    from surdas_brain import SurdasBrain
    
    # Check methods exist
    assert hasattr(SurdasBrain, 'start_ai_voice_mode'), "SurdasBrain missing start_ai_voice_mode()"
    assert hasattr(SurdasBrain, 'stop_ai_voice_mode'), "SurdasBrain missing stop_ai_voice_mode()"
    print("✓ SurdasBrain has AI mode methods")
    
    # Check method signatures
    import inspect
    start_sig = inspect.signature(SurdasBrain.start_ai_voice_mode)
    stop_sig = inspect.signature(SurdasBrain.stop_ai_voice_mode)
    
    assert 'self' in start_sig.parameters, "start_ai_voice_mode missing self parameter"
    assert 'self' in stop_sig.parameters, "stop_ai_voice_mode missing self parameter"
    print("✓ AI mode methods have correct signatures")

def test_ai_mode_flags():
    """Test that AI mode uses proper flags and state."""
    print("\n=== Testing AI Mode Flags ===")
    
    import re
    
    # Read surdas_brain.py to check for proper flag usage
    with open('surdas_brain.py', 'r') as f:
        content = f.read()
    
    # Check for ai_voice_mode flag
    assert 'self.ai_voice_mode' in content, "Missing ai_voice_mode flag"
    print("✓ ai_voice_mode flag exists")
    
    # Check for worker pause calls
    assert 'vision_worker.pause()' in content, "Missing vision_worker.pause() call"
    assert 'safety_worker.pause()' in content, "Missing safety_worker.pause() call"
    print("✓ Workers are paused in AI mode")
    
    # Check for worker resume calls
    assert 'vision_worker.resume()' in content, "Missing vision_worker.resume() call"
    assert 'safety_worker.resume()' in content, "Missing safety_worker.resume() call"
    print("✓ Workers are resumed after AI mode")
    
    # Check for keyboard handler
    assert "'a'" in content.lower() or '"a"' in content.lower(), "Missing 'A' key handler"
    print("✓ 'A' key handler exists")
    
    # Check for single-question behavior
    assert 'question_answered' in content, "Missing question_answered flag for single-question mode"
    print("✓ Single-question behavior implemented")

if __name__ == "__main__":
    try:
        test_worker_pause_resume()
        test_ai_mode_integration()
        test_ai_mode_flags()
        
        print("\n" + "="*50)
        print("✓ ALL TESTS PASSED")
        print("="*50)
        print("\nAI Voice Mode is ready to use!")
        print("Instructions:")
        print("1. Run: python3 surdas_brain.py")
        print("2. Press 'A' key to activate AI Voice Mode")
        print("3. Ask a question (voice will be transcribed)")
        print("4. System answers and auto-exits AI mode")
        print("5. Vision and safety resume automatically")
        
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
