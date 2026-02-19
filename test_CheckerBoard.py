import time
import cv2
import matplotlib.pyplot as plt
from PIDController import PIDController

# This file is used to test the velocity estimation methods on recorded video footage from the drone. 

# velocity_estimator = VelocityEstimator(method="optical_flow")\
# cap = cv2.VideoCapture("output_light.mp4")
# cap = cv2.VideoCapture(0)

drone_url = "rtsp://192.168.1.1:7070/webcam"
cap = cv2.VideoCapture(drone_url)

pid_x = PIDController(0.5, 0.5, 0.5)
pid_y = PIDController(0.5, 0.5, 0.5)


ret, img = cap.read()
if not ret:
    print("Could not get video frame. Exiting.")
    exit(0)

image_height, image_width = img.shape[:2]
center_x, center_y = image_width // 2, image_height // 2

sizes = []
checkerboard_size = (5,5)
count = 0
times = []
while(True):
    count += 1
    for _ in range(2):
        cap.grab()
    ret, img = cap.read()
    if not ret:
        print("Could not get video frame, retrying...")
        continue

    start_time = time.perf_counter()
    # Processing
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    flags = cv2.CALIB_CB_ADAPTIVE_THRESH + cv2.CALIB_CB_NORMALIZE_IMAGE
    ret, corners = cv2.findChessboardCorners(gray, checkerboard_size, flags=flags)
    if ret:
        # cv2.drawChessboardCorners(gray, checkerboard_size, corners, ret)
        check_center_x, check_center_y = corners[12, 0, :] # index 5 (of 16) is close to the center of the 4x4 checkerboard 
        check_center_x, check_center_y = int(check_center_x), int(check_center_y)
        cv2.circle(gray, (check_center_x, check_center_y), 20, 255, -1)
        cv2.circle(gray, (int(corners[0, 0, 0]), int(corners[0, 0, 1])), 20, 200, -1)
        cv2.circle(gray, (int(corners[-1, 0, 0]), int(corners[-1, 0, 1])), 20, 200, -1)


        checker_box_size = (corners[0, 0, :] - corners[-1, 0, :])
        checker_size = (checker_box_size[0] ** 2 +  checker_box_size[1] ** 2) ** (0.5)
        print(checker_size)
        end_time = time.perf_counter()
        times.append(end_time - start_time)
        sizes.append(checker_size)
        print("Found, processing time: {:.4f} seconds".format(end_time - start_time))
    else:
        print("Not found.")



    cv2.imshow("Video", gray)
    key = cv2.waitKey(1) & 0xFF
    
    if key == ord('q'):
        break

print(f"Average processing time per frame: {sum(times)/len(times):.4f} seconds")

distances = []
f = (175 * 45) / 7 # At 45 inches from the checkerboard, the 7 inch diagonal measures approximately 175 pixels.
distances = [f * 7 / size for size in sizes]

plt.plot(sizes)
plt.plot(distances)
plt.show()

cap.release()
cv2.destroyAllWindows()