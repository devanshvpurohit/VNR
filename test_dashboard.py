#!/usr/bin/env python3
"""
Test script for SURDAS Caregiver Dashboard
Sends test events to verify dashboard connectivity and features
"""

import time
import random
from telemetry import start_telemetry, broadcast_event

def test_dashboard():
    """Send test events to dashboard for testing"""
    
    print("=" * 60)
    print("SURDAS Dashboard Test Suite")
    print("=" * 60)
    print("\nStarting telemetry server...")
    
    # Start telemetry server
    start_telemetry(port=8000)
    time.sleep(2)
    
    print("✅ Telemetry server started")
    print("📱 Open dashboard at: http://localhost:5173")
    print("\nSending test events in 5 seconds...")
    time.sleep(5)
    
    # Test 1: Vision Context
    print("\n[1/8] Testing vision context...")
    broadcast_event('vision', {
        'mode': 'NAV',
        'torch_on': False,
        'detected_objects': ['person', 'chair', 'door', 'table'],
        'closest_obstacle': 'chair (1.5m)',
        'wall_ahead': False,
        'fps': 25
    })
    time.sleep(2)
    
    # Test 2: Speech Event
    print("[2/8] Testing speech event...")
    broadcast_event('speech', {
        'text': 'Guide me to the kitchen'
    })
    time.sleep(2)
    
    # Test 3: Indoor Navigation - Start
    print("[3/8] Testing navigation start...")
    broadcast_event('indoor_navigation', {
        'state': 'NAVIGATING',
        'destination': 'kitchen',
        'confidence': 'HIGH',
        'distance_remaining': 5.2,
        'safe_directions': 3,
        'hold_reason': None
    })
    time.sleep(3)
    
    # Test 4: Room Labeled
    print("[4/8] Testing room labeling...")
    broadcast_event('room_labeled', {
        'name': 'Living Room',
        'room_id': 1,
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ')
    })
    time.sleep(2)
    
    # Test 5: Landmark Labeled
    print("[5/8] Testing landmark labeling...")
    broadcast_event('landmark_labeled', {
        'name': 'Kitchen Entrance',
        'landmark_id': 1,
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ')
    })
    time.sleep(2)
    
    # Test 6: Navigation Safety Hold
    print("[6/8] Testing safety hold...")
    broadcast_event('indoor_navigation', {
        'state': 'SAFETY_HOLD',
        'destination': 'kitchen',
        'confidence': 'LOW',
        'distance_remaining': 3.8,
        'safe_directions': 0,
        'hold_reason': 'Obstacle detected ahead'
    })
    time.sleep(3)
    
    # Test 7: Alert
    print("[7/8] Testing alert event...")
    broadcast_event('alert', {
        'message': '⚠️ Low confidence - Limited visibility',
        'priority': 'high'
    })
    time.sleep(2)
    
    # Test 8: Navigation Arrived
    print("[8/8] Testing navigation completion...")
    broadcast_event('indoor_navigation', {
        'state': 'ARRIVED',
        'destination': 'kitchen',
        'confidence': 'HIGH',
        'distance_remaining': 0.0,
        'safe_directions': 4,
        'hold_reason': None
    })
    time.sleep(2)
    
    print("\n" + "=" * 60)
    print("✅ All test events sent successfully!")
    print("=" * 60)
    print("\n📊 Check your dashboard for:")
    print("  • Vision system updates (4 objects detected)")
    print("  • Speech command in activity log")
    print("  • Navigation flow (start → hold → arrived)")
    print("  • Spatial memory (2 new locations)")
    print("  • Alert notification")
    print("\n🔄 Sending continuous updates for 60 seconds...")
    print("   (Press Ctrl+C to stop)")
    
    # Continuous updates
    try:
        for i in range(60):
            # Random object detection
            objects = random.sample(['person', 'chair', 'table', 'door', 'cup', 'laptop', 'phone'], k=random.randint(2, 5))
            broadcast_event('vision', {
                'mode': random.choice(['IDLE', 'NAV', 'OCR']),
                'torch_on': random.choice([True, False]),
                'detected_objects': objects,
                'closest_obstacle': random.choice([None, 'chair (1.2m)', 'table (2.0m)', 'person (3.5m)']),
                'wall_ahead': random.choice([True, False]),
                'fps': random.randint(20, 30)
            })
            
            # Random system metrics
            broadcast_event('metrics', {
                'uptime': i + 300,
                'cpu_usage': random.randint(20, 60),
                'memory_usage': random.randint(40, 80),
                'temperature': random.randint(45, 65)
            })
            
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\n🛑 Test interrupted by user")
    
    print("\n✨ Test complete! Dashboard should still be running.")
    print("   Keep backend alive or Ctrl+C to exit")
    
    # Keep server alive
    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")

if __name__ == '__main__':
    test_dashboard()
