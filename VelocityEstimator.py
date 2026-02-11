from extractor import Frame, match_frames
import cv2
import numpy as np

class VelocityEstimator:
    """
    This class estimates the drone's velocity based on the video feed from the drone's camera.
    It has two methods for estimating velocity: feature matching and optical flow.
    These methods are discussed further in the README.md
    """
    def __init__(self, method='feature_matching'):
        self.previous_frame = None
        self.method = method
        # These four parameters are used for the feature matching
        # F has not been calculated yet, but should be able to work with PID tuning and tuning the match filtering in the match_frames function.
        self.W, self.H = 640 // 2,  480 // 2
        self.F = 450
        self.K = np.array([[self.F, 0, self.W // 2], [0, self.F, self.H // 2], [0, 0, 1]])

        if self.method == "feature_matching":
            self.estimate_velocity = self.estimate_velocity_feature_matching
        elif self.method == "optical_flow":
            self.estimate_velocity = self.estimate_velocity_optical_flow
        else:
            raise ValueError("Unknown method")
        
    # This method is from the SLAM tutorial by LearnOpenCV: https://learnopencv.com/monocular-slam-in-python/
    def estimate_velocity_feature_matching(self, img):
        current_frame = Frame(img, self.K)

        if self.previous_frame is None:
            self.previous_frame = current_frame
            return None
        
        idx1, idx2 = match_frames(self.previous_frame, current_frame) # Match descriptors between the previous and current frame 
        if idx1 is None:
            return None
        
        control_deltas = current_frame.pts[idx2] - self.previous_frame.pts[idx1] # Get the pixel deltas for the matched features between the previous and current frame
        self.previous_frame = current_frame
        return np.mean(control_deltas[..., 0]) # Use the mean of these deltas in the x direction as the velocity estimate for the drone. 
     
    # This method is based on the tutorial from OpenCV on dense optical flow: https://docs.opencv.org/4.x/d4/dee/tutorial_optical_flow.html
    def estimate_velocity_optical_flow(self, img):
        frame2 = cv2.resize(img, (320, 240), interpolation=cv2.INTER_AREA)
        next = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
        if self.previous_frame is None:
            self.previous_frame = next
            return None

        flow = cv2.calcOpticalFlowFarneback(self.previous_frame, next, None, 0.5, 3, 10, 5, 5, 1.2, 0)
        self.previous_frame = next

        # Suppress brightest pixels which are likely to be noisy in the optical flow output.
        threshold = 225  
        flow_x = flow[..., 0]
        flow_x[next > threshold] = 0
        flow_x_data = flow_x.flatten()

        # If the flow is mostly in one direction, take only the data in that direction to get a more accurate estimate of the velocity.
        proportion = np.sum([flow_x_data > 0])/flow_x_data.size
        if abs(proportion - 0.5) > 0.05:
            if proportion > 0.5:
                flow_x_data = flow_x_data[flow_x_data > 0]
            else:
                flow_x_data = flow_x_data[flow_x_data < 0]

        abs_flow_x_data = np.abs(flow_x_data)

        # Only take the top 20% of the flow data, as most of the vectors are close to 0
        threshold = np.percentile(abs_flow_x_data, 80)
        top_20_percent = flow_x_data[abs_flow_x_data >= threshold]
        return np.mean(top_20_percent)
    