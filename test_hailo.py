#!/usr/bin/env python3
"""
Quick test script to verify Hailo setup
"""
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_hailo_sdk():
    """Test if Hailo Platform SDK is installed"""
    try:
        import hailo_platform
        logger.info("✓ Hailo Platform SDK is installed")
        return True
    except ImportError as e:
        logger.error(f"✗ Hailo Platform SDK not found: {e}")
        logger.error("  Install with: sudo apt install hailo-all")
        return False


def test_hailo_device():
    """Test if Hailo device is accessible"""
    import os
    if os.path.exists("/dev/hailo0"):
        logger.info("✓ Hailo device found at /dev/hailo0")
        return True
    else:
        logger.error("✗ Hailo device not found at /dev/hailo0")
        logger.error("  Check device connection and drivers")
        return False


def test_model_files():
    """Test if model files exist"""
    import os
    model_path = "/usr/share/hailo-models/yolov8s_h8l.hef"

    if os.path.exists(model_path):
        size_mb = os.path.getsize(model_path) / (1024 * 1024)
        logger.info(f"✓ YOLOv8 model found ({size_mb:.1f} MB)")
        return True
    else:
        logger.error(f"✗ Model not found at {model_path}")
        logger.error("  Check /usr/share/hailo-models/ for available models")
        return False


def test_dependencies():
    """Test Python dependencies"""
    deps = {
        'numpy': 'numpy',
        'cv2': 'opencv-python',
        'gi': 'pygobject',
        'websockets': 'websockets'
    }

    all_ok = True
    for module, package in deps.items():
        try:
            __import__(module)
            logger.info(f"✓ {package} is installed")
        except ImportError:
            logger.error(f"✗ {package} not found")
            logger.error(f"  Install with: pip install {package}")
            all_ok = False

    return all_ok


def test_hailo_inference():
    """Test basic Hailo inference"""
    try:
        from hailo_inference import HailoDetector
        import numpy as np

        logger.info("Testing Hailo inference...")

        # Create detector
        detector = HailoDetector(
            hef_path="/usr/share/hailo-models/yolov8s_h8l.hef",
            confidence_threshold=0.5
        )

        # Create dummy frame (640x640 RGB)
        test_frame = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)

        # Run inference
        detections, inference_time = detector.infer(test_frame)

        logger.info(f"✓ Hailo inference successful!")
        logger.info(f"  Inference time: {inference_time:.1f}ms")
        logger.info(f"  Detections: {len(detections)}")

        detector.cleanup()
        return True

    except Exception as e:
        logger.error(f"✗ Hailo inference test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    logger.info("=" * 60)
    logger.info("Hailo Setup Verification")
    logger.info("=" * 60)
    logger.info("")

    results = {}

    # Run tests
    logger.info("1. Checking Hailo Platform SDK...")
    results['sdk'] = test_hailo_sdk()
    logger.info("")

    logger.info("2. Checking Hailo device...")
    results['device'] = test_hailo_device()
    logger.info("")

    logger.info("3. Checking model files...")
    results['models'] = test_model_files()
    logger.info("")

    logger.info("4. Checking Python dependencies...")
    results['deps'] = test_dependencies()
    logger.info("")

    # Only test inference if previous tests passed
    if all([results['sdk'], results['device'], results['models'], results['deps']]):
        logger.info("5. Testing Hailo inference...")
        results['inference'] = test_hailo_inference()
        logger.info("")
    else:
        logger.warning("5. Skipping inference test (prerequisites not met)")
        results['inference'] = False
        logger.info("")

    # Summary
    logger.info("=" * 60)
    logger.info("Summary:")
    logger.info("=" * 60)

    total = len(results)
    passed = sum(results.values())

    for test, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"{test.upper()}: {status}")

    logger.info("")
    logger.info(f"Result: {passed}/{total} tests passed")

    if passed == total:
        logger.info("")
        logger.info("🎉 All tests passed! Hailo is ready to use.")
        logger.info("")
        logger.info("Next steps:")
        logger.info("  1. Start backend: python3 server_multi_rtsp.py")
        logger.info("  2. Start Hailo: ./start-hailo-inference.sh")
        logger.info("  3. Start frontend: cd frontend && npm run dev")
        return 0
    else:
        logger.info("")
        logger.info("⚠️  Some tests failed. Fix the issues above before proceeding.")
        logger.info("")
        logger.info("See HAILO_SETUP.md for detailed setup instructions.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
