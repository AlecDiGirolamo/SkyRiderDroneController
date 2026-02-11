import socket
import threading

class FlightController:
    """
    The FlightController class is responsible for managing the control state of the drone and sending control packets to the drone over a UDP socket. 
    It maintains the current control inputs (turn, accelerator, roll, pitch) and various flags for special modes (fast fly, fast drop, emergency stop, etc.).
    To use this class, an instantiation should be created, and then the set_command_state method can be called to update the control inputs and flags.
    send_control_packet should be called in a loop to continuously send the latest control state to the drone.
    The setters, getters, and send_packet methods are all thread-safe, allowing for control state updates and packet sending to happen concurrently.

    The loop responsible for sending control packets to the drone should look something like this:
    while True:
        # Get the trims for the controls
        # Set the control state to trim + joystick input
        # Set any special mode flags based on button presses
        # Send the control packet to the drone
    """
    def __init__(self):

        """
        Docstring for __init__
        
        :param self: Description
        """
        self._lock = threading.Lock()
        self.is_fast_fly = False
        self.is_fast_drop = False
        self.is_emergency_stop = False
        self.is_circle_turn_end = False
        self.is_no_head_mode = False
        self.is_gyro_correction = False

        self.control_turn = 128
        self.control_accelerator = 128
        self.control_roll = 128
        self.control_pitch = 128

        self.control_turn_center = 128
        self.control_accelerator_center = 128
        self.control_roll_center = 128
        self.control_pitch_center = 128

        # Open a socket for sending control packets
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.control_packet_ip =  "192.168.1.1"
        self.control_packet_port = 7099

    def construct_packet(self):
        """
        A helper function used to construct a packet from the current control state.
        """
        packet = bytearray(9)
        with self._lock:
            flags = 0
            if self.is_fast_fly:
                flags |= 0b00000001
            if self.is_fast_drop:
                flags |= 0b00000010
            if self.is_emergency_stop:
                flags |= 0b00000100
            if self.is_circle_turn_end:
                flags |= 0b00001000
            if self.is_no_head_mode:
                flags |= 0b00010000
            if self.is_gyro_correction:
                flags |= 0b10000000
            # The Sky Cruise app used the following two lines to reduce joystick drift,
            # but it seems unnecessary for programmatic control.
            # if self.control_turn >= 104 and self.control_turn <= 152: 
                # self.control_turn = 128 

            # Sanitize control inputs
            # Setting the control input to 1 was how the Sky Cruise app seemed to handle the deadzone for the controls so it was kept the same here.
            if self.control_turn < 1:
                self.control_turn = 1
            elif self.control_turn > 255:
                self.control_turn = 255
            
            if self.control_accelerator == 1:
                self.control_accelerator = 0
            elif self.control_accelerator > 255:
                self.control_accelerator = 255
            elif self.control_accelerator <= 1:
                self.control_accelerator = 0

            if self.control_roll < 1:
                self.control_roll = 1
            elif self.control_roll > 255:
                self.control_roll = 255
            
            if self.control_pitch < 1:
                self.control_pitch = 1
            elif self.control_pitch > 255:
                self.control_pitch = 255

            check_sum = self.control_roll
            check_sum ^= self.control_pitch
            check_sum ^= self.control_accelerator
            check_sum ^= self.control_turn
            check_sum ^= (flags & 0xFF)


            packet[0] = 0x03  # Header
            packet[1] = 0x66
            packet[2] = self.control_roll
            packet[3] = self.control_pitch
            packet[4] = self.control_accelerator
            packet[5] = self.control_turn
            packet[6] = flags
            packet[7] = check_sum
            packet[8] = 0x99  # Footer
            
        return packet
    
    def set_command_state(self, control_turn = None, control_accelerator = None, control_roll = None, control_pitch = None, 
                          is_fast_fly = False, is_fast_drop = False, is_emergency_stop = False, is_circle_turn_end = False, is_no_head_mode = False, is_gyro_correction = False):
        """
        Docstring for set_command_state
        
        :param control_turn: yaw axis control input (0-255, where control_turn_center is neutral)
        :param control_accelerator: throttle control input (0-255, where control_accelerator_center is neutral)
        :param control_roll: roll axis control input (0-255, where control_roll_center is neutral)
        :param control_pitch: pitch axis control input (0-255, where control_pitch_center is neutral)
        :param is_fast_fly: Set to true to take off.
        :param is_fast_drop: Set to true to land.
        :param is_emergency_stop: Set to true to immediately stop all motors.
        :param is_circle_turn_end: TODO: Check functionality of flag
        :param is_no_head_mode: TODO: Check functionality of flag
        :param is_gyro_correction: Set to true to enable gyro correction (meant to be set briefly before takeoff)
        """
        with self._lock:
            if control_turn is not None:
                self.control_turn = control_turn
            if control_accelerator is not None:
                self.control_accelerator = control_accelerator
            if control_roll is not None:
                self.control_roll = control_roll
            if control_pitch is not None:
                self.control_pitch = control_pitch

            self.is_fast_fly = is_fast_fly
            self.is_fast_drop = is_fast_drop
            self.is_emergency_stop = is_emergency_stop
            self.is_circle_turn_end = is_circle_turn_end
            self.is_no_head_mode = is_no_head_mode
            self.is_gyro_correction = is_gyro_correction

    def get_command_state(self):
        with self._lock:
            return (self.control_turn, self.control_accelerator, self.control_roll, self.control_pitch,
                    self.is_fast_fly, self.is_fast_drop, self.is_emergency_stop, self.is_circle_turn_end, self.is_no_head_mode, self.is_gyro_correction)

    def get_trims(self):
        return (self.control_turn_center, self.control_accelerator_center,
                self.control_roll_center, self.control_pitch_center)
        
    def set_trims(self, turn_center, accelerator_center, roll_center, pitch_center):
        """
        These trims are meant to be helpers for the user to adjust the neutral point of the controls.
        """
        self.control_turn_center = turn_center
        self.control_accelerator_center = accelerator_center
        self.control_roll_center = roll_center
        self.control_pitch_center = pitch_center

    def send_control_packet(self):
        packet = self.construct_packet()
        self.sock.sendto(packet, (self.control_packet_ip, self.control_packet_port)) 
