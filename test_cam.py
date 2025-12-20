import cv2

for i in range(5):
    cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print(f"Camera {i}: Not available")
        continue

    ret, frame = cap.read()
    if ret and frame is not None:
        print(f"Camera {i}: WORKING")
    else:
        print(f"Camera {i}: Opened but NOT producing frames")

    cap.release()
