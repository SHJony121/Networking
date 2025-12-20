"""
Quick camera detector - shows all available cameras with preview
"""
import cv2
import time

print("Checking for available cameras...\n")

available_cameras = []

for i in range(10):  # Check first 10 indexes
    cap = cv2.VideoCapture(i)
    if cap.isOpened():
        # Try to read a frame
        ret, frame = cap.read()
        if ret:
            print(f"✓ Camera {i}: AVAILABLE and working")
            print(f"  Resolution: {int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x{int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))}")
            available_cameras.append(i)
            
            # Show a preview window for 2 seconds
            cv2.imshow(f"Camera {i} Preview (will close in 2s)", frame)
            cv2.waitKey(2000)
            cv2.destroyAllWindows()
        else:
            print(f"✗ Camera {i}: Opened but can't read frames")
        cap.release()
    else:
        print(f"✗ Camera {i}: Not available")

print(f"\n{'='*50}")
print(f"Summary: Found {len(available_cameras)} working camera(s)")
print(f"Camera indexes: {available_cameras}")
print(f"{'='*50}")

if len(available_cameras) >= 2:
    print(f"\nFor testing:")
    print(f"  jny (host):   Use camera index {available_cameras[0]} (default)")
    print(f"  yoyo (client): Use camera index {available_cameras[1]}")
    print(f"\n  Start yoyo with:")
    print(f"    set CAMERA_INDEX={available_cameras[1]}")
    print(f"    python main.py")
elif len(available_cameras) == 1:
    print(f"\n⚠ Warning: Only 1 camera detected!")
    print(f"  Make sure iVCam is running and connected")
else:
    print(f"\n⚠ Error: No cameras detected!")
