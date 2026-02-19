"""
Test script for Video Skill Service
Tests REST API and WebSocket endpoints
"""
import asyncio
import json
import time
from datetime import datetime

import requests
import websockets


BASE_URL = "http://localhost:8888"
WS_URL = "ws://localhost:8888"


def test_health():
    """Test health check endpoint"""
    print("\n=== Testing Health Check ===")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200


def test_list_cameras():
    """Test camera list endpoint"""
    print("\n=== Testing Camera List ===")
    response = requests.get(f"{BASE_URL}/cameras")
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Cameras found: {len(data['cameras'])}")
    for camera in data['cameras']:
        print(f"  - {camera['id']}: {camera['name']} (connected={camera['connected']})")
    return response.status_code == 200


def test_capture_frame(camera_id: str = "camera1"):
    """Test frame capture with inference"""
    print(f"\n=== Testing Frame Capture ({camera_id}) ===")
    response = requests.post(
        f"{BASE_URL}/cameras/{camera_id}/capture",
        json={
            "save_frame": True,
            "run_inference": True
        }
    )
    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"Timestamp: {datetime.fromtimestamp(data['timestamp'])}")
        print(f"Detections: {len(data['detections'])}")
        for det in data['detections']:
            print(f"  - {det['class_name']}: {det['confidence']:.2f}")
        print(f"Frame saved: {data['file_path']}")

    return response.status_code == 200


def test_start_recording(camera_id: str = "camera1", duration: int = 10):
    """Test video recording"""
    print(f"\n=== Testing Recording Start ({camera_id}, {duration}s) ===")
    response = requests.post(
        f"{BASE_URL}/cameras/{camera_id}/record/start",
        json={
            "duration_seconds": duration,
            "include_detections": True
        }
    )
    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"Recording ID: {data['recording_id']}")
        print(f"Status: {data['status']}")
        return data['recording_id']

    return None


def test_stop_recording(camera_id: str = "camera1"):
    """Test stopping recording"""
    print(f"\n=== Testing Recording Stop ({camera_id}) ===")
    response = requests.post(f"{BASE_URL}/cameras/{camera_id}/record/stop")
    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"Recording ID: {data['recording_id']}")
        print(f"Status: {data['status']}")

    return response.status_code == 200


def test_list_recordings(camera_id: str = None):
    """Test recording list"""
    print(f"\n=== Testing Recording List ===")
    params = {"camera_id": camera_id} if camera_id else {}
    response = requests.get(f"{BASE_URL}/recordings", params=params)
    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"Recordings: {data['count']}")
        for rec in data['recordings'][:5]:  # Show first 5
            print(f"  - ID {rec['id']}: {rec['camera_id']} ({rec['status']})")
            print(f"    Duration: {rec['end_time'] - rec['start_time']:.1f}s" if rec['end_time'] else "    Still recording")
            print(f"    Detections: {rec['detection_count']}")

    return response.status_code == 200


def test_query_detections(camera_id: str = None):
    """Test detection query"""
    print(f"\n=== Testing Detection Query ===")
    response = requests.post(
        f"{BASE_URL}/detections/query",
        json={
            "camera_id": camera_id,
            "min_confidence": 0.5,
            "limit": 10
        }
    )
    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"Detections found: {data['count']}")
        for det in data['detections'][:5]:  # Show first 5
            ts = datetime.fromtimestamp(det['timestamp'])
            print(f"  - {ts}: {det['class_name']} ({det['confidence']:.2f}) on {det['camera_id']}")

    return response.status_code == 200


def test_detection_stats(camera_id: str = None):
    """Test detection statistics"""
    print(f"\n=== Testing Detection Stats ===")
    params = {"camera_id": camera_id, "hours": 24} if camera_id else {"hours": 24}
    response = requests.get(f"{BASE_URL}/detections/stats", params=params)
    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"Total detections (last {data['time_window_hours']}h): {data['total_detections']}")
        print("Class breakdown:")
        for class_name, count in sorted(data['class_counts'].items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  - {class_name}: {count}")

    return response.status_code == 200


async def test_websocket_stream(camera_id: str = "camera1", duration: int = 5):
    """Test WebSocket live streaming"""
    print(f"\n=== Testing WebSocket Stream ({camera_id}, {duration}s) ===")

    uri = f"{WS_URL}/ws/{camera_id}/stream?detections=true"
    print(f"Connecting to: {uri}")

    try:
        async with websockets.connect(uri) as websocket:
            print("Connected! Receiving frames...")

            start_time = time.time()
            frame_count = 0

            while time.time() - start_time < duration:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    data = json.loads(message)

                    if data['type'] == 'frame':
                        frame_count += 1
                        det_count = len(data['detections'])
                        print(f"Frame {frame_count}: {det_count} detections", end='\r')

                except asyncio.TimeoutError:
                    print("\nTimeout waiting for frame")
                    break

            print(f"\nReceived {frame_count} frames in {duration}s ({frame_count/duration:.1f} FPS)")
            return True

    except Exception as e:
        print(f"WebSocket error: {e}")
        return False


def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("Video Skill Service Test Suite")
    print("=" * 60)

    results = {}

    # REST API tests
    results['health'] = test_health()
    results['list_cameras'] = test_list_cameras()
    results['capture_frame'] = test_capture_frame()

    # Recording tests
    recording_id = test_start_recording(duration=5)
    if recording_id:
        print(f"\nWaiting 5 seconds for recording to complete...")
        time.sleep(6)
        results['stop_recording'] = test_stop_recording()
    else:
        results['start_recording'] = False

    results['list_recordings'] = test_list_recordings()

    # Detection tests
    results['query_detections'] = test_query_detections()
    results['detection_stats'] = test_detection_stats()

    # WebSocket test
    print("\nRunning WebSocket test (this will take 5 seconds)...")
    results['websocket_stream'] = asyncio.run(test_websocket_stream())

    # Summary
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, passed_test in results.items():
        status = "✓ PASS" if passed_test else "✗ FAIL"
        print(f"{status}: {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    return passed == total


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        # Run specific test
        test_name = sys.argv[1]
        test_func = globals().get(f"test_{test_name}")
        if test_func:
            test_func()
        else:
            print(f"Unknown test: {test_name}")
            print("Available tests:")
            for name in dir():
                if name.startswith("test_") and callable(globals()[name]):
                    print(f"  - {name[5:]}")
    else:
        # Run all tests
        success = run_all_tests()
        sys.exit(0 if success else 1)
