"""
Test Script - Verify project setup and dependencies
"""
import sys

def test_imports():
    """Test if all required libraries are installed"""
    print("Testing imports...")
    errors = []
    
    # Test PyQt5
    try:
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtCore import Qt
        from PyQt5.QtGui import QFont
        print("✓ PyQt5 installed")
    except ImportError as e:
        errors.append(f"✗ PyQt5 not found: {e}")
    
    # Test OpenCV
    try:
        import cv2
        print(f"✓ OpenCV installed (version {cv2.__version__})")
    except ImportError as e:
        errors.append(f"✗ OpenCV not found: {e}")
    
    # Test PyAudio
    try:
        import pyaudio
        print("✓ PyAudio installed")
    except ImportError as e:
        errors.append(f"✗ PyAudio not found: {e}")
    
    # Test Matplotlib
    try:
        import matplotlib
        print(f"✓ Matplotlib installed (version {matplotlib.__version__})")
    except ImportError as e:
        errors.append(f"✗ Matplotlib not found: {e}")
    
    # Test NumPy
    try:
        import numpy
        print(f"✓ NumPy installed (version {numpy.__version__})")
    except ImportError as e:
        errors.append(f"✗ NumPy not found: {e}")
    
    return errors

def test_camera():
    """Test camera availability"""
    print("\nTesting camera...")
    try:
        import cv2
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            ret, frame = cap.read()
            cap.release()
            if ret:
                print("✓ Camera working")
                return True
            else:
                print("✗ Camera opened but cannot read frames")
                return False
        else:
            print("✗ Cannot open camera (check permissions)")
            return False
    except Exception as e:
        print(f"✗ Camera test failed: {e}")
        return False

def test_audio():
    """Test audio device availability"""
    print("\nTesting audio...")
    try:
        import pyaudio
        p = pyaudio.PyAudio()
        device_count = p.get_device_count()
        print(f"✓ Found {device_count} audio devices")
        
        # List audio devices
        print("\nAvailable audio devices:")
        for i in range(device_count):
            info = p.get_device_info_by_index(i)
            if info['maxInputChannels'] > 0:
                print(f"  [{i}] {info['name']} (Input)")
        
        p.terminate()
        return True
    except Exception as e:
        print(f"✗ Audio test failed: {e}")
        return False

def test_file_structure():
    """Test if all required files exist"""
    print("\nTesting file structure...")
    import os
    
    required_files = [
        'common/protocol.py',
        'server/server_main.py',
        'server/meeting_manager.py',
        'server/control_handler.py',
        'server/stream_relay_udp.py',
        'server/congestion_control.py',
        'client/main.py',
        'client/tcp_control.py',
        'client/video_sender.py',
        'client/video_receiver.py',
        'client/audio_sender.py',
        'client/audio_receiver.py',
        'client/stats_collector.py',
        'client/stats_window.py',
        'client/tcp_file_transfer.py',
        'client/ui_home.py',
        'client/ui_waiting_room.py',
        'client/ui_meeting.py'
    ]
    
    missing = []
    for filepath in required_files:
        if os.path.exists(filepath):
            print(f"✓ {filepath}")
        else:
            print(f"✗ {filepath} MISSING")
            missing.append(filepath)
    
    return missing

def main():
    """Run all tests"""
    print("=" * 60)
    print("Multi-Client Real-Time Communication System")
    print("Setup Verification Test")
    print("=" * 60)
    
    # Test imports
    import_errors = test_imports()
    
    # Test file structure
    missing_files = test_file_structure()
    
    # Test hardware
    camera_ok = test_camera()
    audio_ok = test_audio()
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    if import_errors:
        print("\n❌ MISSING DEPENDENCIES:")
        for error in import_errors:
            print(f"  {error}")
        print("\nRun: pip install -r requirements.txt")
    else:
        print("✓ All dependencies installed")
    
    if missing_files:
        print("\n❌ MISSING FILES:")
        for filepath in missing_files:
            print(f"  {filepath}")
    else:
        print("✓ All files present")
    
    if not camera_ok:
        print("\n⚠ Camera not available (may need permissions)")
    else:
        print("✓ Camera working")
    
    if not audio_ok:
        print("\n⚠ Audio device issue")
    else:
        print("✓ Audio devices found")
    
    # Final verdict
    print("\n" + "=" * 60)
    if not import_errors and not missing_files:
        print("✅ READY TO RUN!")
        print("\nNext steps:")
        print("  1. cd server && python server_main.py")
        print("  2. cd client && python main.py")
    else:
        print("❌ SETUP INCOMPLETE")
        print("\nFix the issues above and run this test again")
    print("=" * 60)

if __name__ == '__main__':
    main()
