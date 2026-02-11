import time
from VelocityEstimator import VelocityEstimator
import cv2
import matplotlib.pyplot as plt

# This file is used to test the velocity estimation methods on recorded video footage from the drone. 

# velocity_estimator = VelocityEstimator(method="optical_flow")
velocity_estimator = VelocityEstimator(method="feature_matching")
cap = cv2.VideoCapture("output_light.mp4")
frame_rate = cap.get(cv2.CAP_PROP_FPS)
dt = 1 / frame_rate
t = 0
timeline = []
velocities = []
count = 0
times = []
while(True):
    count += 1
    for _ in range(2):
        cap.grab()
    ret, img = cap.read()
    if not ret:
        print("Finished video.")
        break

    start_time = time.perf_counter()
    velocity = velocity_estimator.estimate_velocity(img)
    end_time = time.perf_counter()
    if velocity is not None:
        times.append(end_time - start_time)
        velocities.append(velocity)
        timeline.append(t)
        print("t: ", t, " | Velocity: ", velocity)
    else:
        print("No Velocity")
    t += dt
    cv2.imshow("Video", img)
    key = cv2.waitKey(1) & 0xFF
    
    if key == ord('q'):
        break
print(f"Average processing time per frame: {sum(times)/len(times):.4f} seconds")

plt.plot(timeline, velocities)
plt.xlabel("Time (s)")
plt.ylabel("Horizontal Velocity")
plt.hlines([0], timeline[0], timeline[-1], colors='r', linestyles='dashed')
plt.show()

cap.release()
cv2.destroyAllWindows()