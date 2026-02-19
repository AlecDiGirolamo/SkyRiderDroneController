import keyboard
import time
import cv2
import threading
import csv

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
        control_authority = 32
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


def get_latest_frame(cap, lock, counter, quitting):
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
    while not quitting.is_set():
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
    - estimate the drone's position using a checkerboard pattern
    - update the PIDController with the error in position.
    - adjust the drone's roll, pitch, and throttle based on the PID output

    The loop then tells the flight controller to send the latest control packet to the drone.
    """

    flight_controller = FlightController()
    pid_x = PIDController(1.5, 0.25, 0.75)
    pid_y = PIDController(1.5, 0.25, 0.75)
    pid_z = PIDController(0.10, 0.025, 0.05)

    drone_url = "rtsp://192.168.1.1:7070/webcam"
    cap = cv2.VideoCapture(drone_url)
    cap_fps = cap.get(cv2.CAP_PROP_FPS)

    ret, img = cap.read()
    if not ret:
        print("Could not get video frame. Exiting.")
        exit(0)

    image_height, image_width = img.shape[:2]
    center_x, center_y = image_width // 2, image_height // 2

    capture_lock = threading.Lock()
    counter = [0]
    quitting = threading.Event()
    quitting.clear()
    frame_cap_thread = threading.Thread(target=get_latest_frame, args=(cap, capture_lock, counter, quitting), daemon=True)
    frame_cap_thread.start()

    auto_pilot_enabled = False
    p_is_pressed = False
    last_frame_num = 0
    frames_to_skip = 2
    time_between_frames = 0.05
    checkerboard_size = (5,5)
    distance_target = 60 # inches
    f = (175 * 45) / 7

    save_video = True
    # For logging PID tuning input and output
    log_data = True
    timeline = []
    log_pid_x = []
    log_error_x = []
    log_pid_y = []
    log_error_y = []
    log_pid_z = []
    log_error_z = []

    out = None
    if save_video:
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter('output.mp4', fourcc, cap_fps, (image_width, image_height))

    log_start_time = time.time()
    while True:
        start_time = time.time()
        key_pressed = handle_keyboard_input(flight_controller)
        if key_pressed:
            auto_pilot_enabled = False
            pid_x.reset()
            pid_y.reset()
            pid_z.reset()


        if keyboard.is_pressed('p'): # Toggle autopilot mode
            if not p_is_pressed:
                print("Toggling Autopilot")
                auto_pilot_enabled = not auto_pilot_enabled
                pid_x.reset()
                pid_y.reset()
                pid_z.reset()
            p_is_pressed = True
        else:
            p_is_pressed = False

        if auto_pilot_enabled:
            with capture_lock:
                ret, img2 = cap.retrieve()
            if not ret:
                print("Failed to read frame")
                continue

            gray = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
            ret, corners = cv2.findChessboardCorners(gray, checkerboard_size, flags=cv2.CALIB_CB_ADAPTIVE_THRESH + cv2.CALIB_CB_NORMALIZE_IMAGE)
            if ret:
                check_center_x, check_center_y = corners[12, 0, :] # index 12 (of 25) is close to the center of the 4x4 checkerboard 
                check_center_x, check_center_y = int(check_center_x), int(check_center_y)
                cv2.circle(img2, (check_center_x, check_center_y), 10, (0, 0, 0), -1) # Place a circle on the center of the checkerboard
                check_diagonal_diff = (corners[0, 0, :] - corners[-1, 0, :])
                check_diagonal_size = (check_diagonal_diff[0] ** 2 +  check_diagonal_diff[1] ** 2) ** (0.5)

                check_distance = f * 7 / check_diagonal_size

                error_z = distance_target - check_distance 
                error_x = (center_x - check_center_x) * check_distance / f
                error_y = (check_center_y - center_y) * check_distance / f
                
                
                control_output_x = pid_x.update(error_x)
                control_output_y = pid_y.update(error_y)
                control_output_z = pid_z.update(error_z)
                if control_output_x > 0 and control_output_x < 13:
                    control_output_x = 13  
                elif control_output_x < 0 and control_output_x > -13:
                    control_output_x = -13

                if control_output_y > 0 and control_output_y < 13:
                    control_output_y = 13  
                elif control_output_y < 0 and control_output_y > -13:
                    control_output_y = -13

                if control_output_z > 0 and control_output_z < 13:
                    control_output_z = 13
                elif control_output_z < 0 and control_output_z > -13:
                    control_output_z = -13

                # Logging 
                log_pid_x.append(control_output_x)
                log_error_x.append(error_x)
                log_pid_y.append(control_output_y)
                log_error_y.append(error_y)
                log_pid_z.append(control_output_z)
                log_error_z.append(error_z)
                timeline.append(time.time() - log_start_time)
                
                flight_controller.set_command_state(
                    control_roll=flight_controller.control_roll_center + int(control_output_x),
                    control_accelerator=flight_controller.control_accelerator_center + int(control_output_y),
                    control_pitch=flight_controller.control_pitch_center + int(control_output_z))

            else:
                print("Checkerboard not found, skipping PID update.")

            # This should be commented out if the processing is running slow
            cv2.imshow("Drone Camera", img2)
            cv2.waitKey(1)
        
        # If autopilot isnt running, show the drone's video feed.
        if not auto_pilot_enabled:
            with capture_lock:
                ret, img2 = cap.retrieve()
                if ret:
                    cv2.imshow("Drone Camera", img2)
                    cv2.waitKey(1)
        
        flight_controller.send_control_packet()
        
        # Press escape to exit the program. Note that the drone will stop receiving control packets, which should cause it to hover or crash.
        if keyboard.is_pressed("esc"):
            print("Exiting program")
            break

        if save_video and img2 is not None:
            if img2 is not None:
                out.write(img2)
        end_time = time.time()
        time.sleep(max(0, time_between_frames - (end_time - start_time))) # If processing is fast, wait before sending the next packet
    
    if log_data:
        with open('log.csv', 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Timeline', 'Error_X', 'Error_Y', 'Error_Z', 'PID_X', 'PID_Y', 'PID_Z'])  # Header
            for i in range(len(timeline)):
                writer.writerow([
                    timeline[i],
                    log_error_x[i] if i < len(log_error_x) else '',
                    log_error_y[i] if i < len(log_error_y) else '',
                    log_error_z[i] if i < len(log_error_z) else '',
                    log_pid_x[i] if i < len(log_pid_x) else '',
                    log_pid_y[i] if i < len(log_pid_y) else '',
                    log_pid_z[i] if i < len(log_pid_z) else ''
                ])

    quitting.set() # Tell camera capture thread to exit.
    frame_cap_thread.join() # Wait for thread to exit
    cap.release()
    cv2.destroyAllWindows()