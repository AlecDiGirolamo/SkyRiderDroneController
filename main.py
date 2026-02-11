import keyboard
import time
import cv2
import threading

from FlightController import FlightController
from PIDController import PIDController
from VelocityEstimator import VelocityEstimator


def handle_keyboard_input(flight_controller : FlightController):
    """
    Process keyboard input and updates the flight controller's command state accordingly. 
    :param flight_controller: FlightController: The flight controller instance to update based on keyboard input.

    Returns: True if any relevant key is pressed, otherwise False.
    
    Key Bindings:
    - Space: Reduce control authority for finer manual control.
    - Enter: Toggle trim mode for adjusting control centers.
    - W/S: Increase/decrease pitch.
    - A/D: Decrease/increase roll.
    - Q/E: Decrease/increase yaw.
    - Shift/Ctrl: Ascend/Descend.
    - Up/Down: Enable fast fly/fast drop modes. fastFly mode is how the drone takes off.
    - Esc: Emergency stop.
    - C: Circle turn end. I haven't observed this flag's behavior.
    - N: No head mode. I haven't observed this flag's behavior.
    - G: Gyro correction. I believe this is for resetting the drone's orientation before takeoff.
    
    Notes:
    - Control authority is 128 by default. Pressing space reduces it to 64 for finer control.
    - Trim mode allows adjusting the control centers for roll, pitch, yaw, and throttle.
    - Multiple keys can be pressed simultaneously for combined actions.
    """
    control_authority = 128
    trim_authority = 1

    key_pressed = False
    if keyboard.is_pressed('space'):
        control_authority = 64
        key_pressed = True

    trim_mode = False
    if keyboard.is_pressed('enter'):
        trim_mode = True
        key_pressed = True


    if trim_mode:
        if keyboard.is_pressed('w'):
            flight_controller.control_pitch_center += trim_authority
        elif keyboard.is_pressed('s'):
            flight_controller.control_pitch_center -= trim_authority
        if keyboard.is_pressed('a'):
            flight_controller.control_roll_center -= trim_authority
        elif keyboard.is_pressed('d'):
            flight_controller.control_roll_center += trim_authority
        if keyboard.is_pressed('q'):
            flight_controller.control_turn_center -= trim_authority
        elif keyboard.is_pressed('e'):
            flight_controller.control_turn_center += trim_authority
        if keyboard.is_pressed('shift'):
            flight_controller.control_accelerator_center += trim_authority  
        elif keyboard.is_pressed('ctrl'):
            flight_controller.control_accelerator_center -= trim_authority
        return 1

    (control_turn, control_accelerator, control_roll, control_pitch) = flight_controller.get_trims()
    if keyboard.is_pressed('w'):
        control_pitch += control_authority
        key_pressed = True
    elif keyboard.is_pressed('s'):
        control_pitch -= control_authority
        key_pressed = True
    if keyboard.is_pressed('a'):
        control_roll -= control_authority
        key_pressed = True
    elif keyboard.is_pressed('d'):
        control_roll += control_authority
        key_pressed = True
    if keyboard.is_pressed('q'):
        control_turn -= control_authority
        key_pressed = True
    elif keyboard.is_pressed('e'):
        control_turn += control_authority
        key_pressed = True
    if keyboard.is_pressed('shift'):
        control_accelerator += control_authority
        key_pressed = True
    elif keyboard.is_pressed('ctrl'):
        control_accelerator -= control_authority
        key_pressed = True

    is_fast_fly = False
    is_fast_drop = False
    is_emergency_stop = False
    is_circle_turn_end = False
    is_no_head_mode = False
    is_gyro_correction = False

    if keyboard.is_pressed('up'):
        is_fast_fly = True
        key_pressed = True
    if keyboard.is_pressed('down'):
        is_fast_drop = True
        key_pressed = True
    if keyboard.is_pressed('esc'):
        is_emergency_stop = True
        key_pressed = True
    if keyboard.is_pressed('c'):
        is_circle_turn_end = True
        key_pressed = True
    if keyboard.is_pressed('n'):
        is_no_head_mode = True
        key_pressed = True
    if keyboard.is_pressed('g'):
        is_gyro_correction = True
        key_pressed = True
    flight_controller.set_command_state(control_turn, control_accelerator, control_roll, control_pitch,
                                       is_fast_fly, is_fast_drop, is_emergency_stop, is_circle_turn_end, is_no_head_mode, is_gyro_correction)        
    return key_pressed


def get_latest_frame(cap, lock, counter):
    """
    Docstring for get_latest_frame
    This function continuously grabs frames from the video capture in a separate thread to ensure that the latest frame is always available for processing.
    This should be run in a seperate thread. If this is not run, the buffer fills and frames read will be late.
    As long as the processing thread does not block the GIL too long, this should allow the main thread to always have access to the latest frame without significant delay.
    
    :param cap: cv2 VideoCapture object for reading video frames.
    :param lock: threading.Lock object to synchronize access to the video capture.
    :param counter: List containing a single integer to keep track of the number of frames captured. 
                    This is used to determine how many frames have been grabbed and skipped during video processing.
    """
    while True:
        with lock:
            cap.grab()
            counter[0] += 1
        time.sleep(0.001)

if __name__ == "__main__":
    """
    main initializes the FlightController, VelocityEstimator, and PIDController. 
    It starts a separate thread to continuously grab frames from the drone's video feed to ensure the latest frame is always available for processing. 
    The main loop handles any keyboard input, and disables autopilot if any key is pressed.
    Pressing 'p' toggles autopilot mode. 
    When autopilot is enabled, the following is performed
    - retrieve the latest frame from the video feed
    - estimate the drone's velocity using the VelocityEstimator
    - update the PIDController with the estimated velocity to get control output
    - adjust the drone's roll based on the PID control output to maintain stable flight

    The loop then tells the flight controller to send the latest control packet to the drone.
    """

    flight_controller = FlightController()
    # velocity_estimator = VelocityEstimator(method="optical_flow")
    # pid_controller = PIDController(kp=0.5, ki=1, kd=0.05) # kp=0.5, ki=1, kd=0.05

    velocity_estimator = VelocityEstimator(method="feature_matching")
    pid_controller = PIDController(kp=300, ki=300, kd=10) # kp=300, ki=300, kd=10 

    drone_url = "rtsp://192.168.1.1:7070/webcam"
    cap = cv2.VideoCapture(drone_url)
    capture_lock = threading.Lock()
    counter = [0]
    threading.Thread(target=get_latest_frame, args=(cap, capture_lock, counter), daemon=True).start()

    auto_pilot_enabled = False
    p_is_pressed = False
    last_frame_num = 0
    frames_to_skip = 2
    time_between_frames = 0.05
    while True:
        start_time = time.time()
        key_pressed = handle_keyboard_input(flight_controller)
        if key_pressed:
            auto_pilot_enabled = False
            pid_controller.reset()
            velocity_estimator.previous_frame = None

        if keyboard.is_pressed('p'): # Toggle autopilot mode
            if not p_is_pressed:
                print("Toggling Autopilot")
                auto_pilot_enabled = not auto_pilot_enabled
                pid_controller.reset()
                velocity_estimator.previous_frame = None
            p_is_pressed = True
        else:
            p_is_pressed = False

        if auto_pilot_enabled:
            with capture_lock:
                curr_frame_num = counter[0]
                # Skip frames to amplify difference between images if the drone is moving slowly.
                skipped_frames = curr_frame_num - last_frame_num
                if skipped_frames < frames_to_skip:
                    for _ in range(frames_to_skip - skipped_frames):
                        cap.grab()
                last_frame_num = curr_frame_num
                ret, img2 = cap.retrieve()
            if not ret:
                print("Failed to read frame")
                continue

            # Estimate the velocity and update the PID controller
            # Use the PID controller to adjust the drone's roll
            velocity = velocity_estimator.estimate_velocity(img2)
            if velocity is not None:
                control_output = pid_controller.update(velocity)
                trim = 128 - int(control_output)
                print("Trim: ", trim, f"Velocity: {velocity:.4f}")
                flight_controller.set_command_state(control_roll=trim)
            else:
                print("Velocity estimation failed, skipping PID update.")

            # This should be commented out if the processing is running slow
            cv2.imshow("Drone Camera", img2)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        # If autopilot isnt running, show the drone's video feed.
        if not auto_pilot_enabled:
            with capture_lock:
                ret, img2 = cap.retrieve()
                if ret:
                    cv2.imshow("Drone Camera", img2)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
        
        # Press escape to exit the program. Note that the drone will stop receiving control packets, which should cause it to hover or crash.
        if keyboard.is_pressed("esc"):
            print("Exiting program")
            break

        flight_controller.send_control_packet()
        end_time = time.time()
        time.sleep(max(0, time_between_frames - (end_time - start_time))) # If processing is fast, wait before sending the next packet
    
    cap.release()
    cv2.destroyAllWindows()