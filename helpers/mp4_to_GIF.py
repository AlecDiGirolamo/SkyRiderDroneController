import cv2
from PIL import Image

video = "Test_300_300.mp4"
cap = cv2.VideoCapture(video)
fps = cap.get(cv2.CAP_PROP_FPS)
frames = []

GIF_speedup_factor = 4
num_skipped_frames = 2
num_frames = 0

while True:
    for _ in range(num_skipped_frames):
        cap.grab()
    ret, frame = cap.read()
    if not ret:
        print("Could not get frame.")
        break
    # Convert BGR to RGB
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    frame_resized = cv2.resize(frame_rgb, (1920//2, 1080//2), interpolation=cv2.INTER_AREA)
    frame_cropped = frame_resized[:, 1920//8:3*1920//8, :]  # Crop to 1600x800
    frames.append(Image.fromarray(frame_cropped))
    cv2.imshow("Frame", frame_cropped)
    cv2.waitKey(1)
    num_frames += 1

cap.release()
print(f"Extracted {num_frames} frames from video.")
# Save as GIF
frames[0].save(video.replace(".mp4", ".gif"), save_all=True, append_images=frames[1:], 
               duration=5, loop=0)  # duration in ms per frame
print("Saved GIF")