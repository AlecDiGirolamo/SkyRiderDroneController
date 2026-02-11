from PIDController import PIDController
import time
import matplotlib.pyplot as plt

# This file simulates a drone's velocity response to changes in trim 
# Changes in trim come from a PID controller which is trying to maintain a velocity of 0 by adjusting the trim based on the velocity estimate.


if __name__ == "__main__":
    kp = 300
    ki = 300
    kd = 1
    pid_controller = PIDController(kp=kp, ki=ki, kd=kd)
    base_controller_center = 128
    f_0 = base_controller_center
    true_center = 140
    v = -0.03

    force_coefficient = 0.01 # Balanced so that steady state velocity without pid is around 0.04 with base_controller_center. 
                            # This is approximately the velocity observed in hover mode when the drone trim is not changed.

    dt = 0.15 # Time step in seconds (approximate time between control updates in real system)
    alpha = 50 # Damping coefficient
    vs = [] # Velocity over time for plotting
    timeline = [] # Time in seconds for each iteration, used for plotting
    start_time = time.time()
    i = 0
    while True:
        # Physical Simulation
        f_total = (f_0 - true_center) * force_coefficient # If the controller is set to the true center, the forces balance out and v approaches 0
        f_total -= alpha * v * abs(v) # Add damping to mimic drone behavior. Coefficient is high to quickly reach terminal velocity.

        v += f_total * dt
        
        # Update trim
        trim = pid_controller.update(v) 
        print("Trim: ", base_controller_center + trim, f"v: {v:.4f}")
        f_0 = base_controller_center + trim

        # For plotting
        current_time = time.time() - start_time
        timeline.append(dt*i)
        vs.append(v)
        
        # Plot trim over time
        plt.cla()
        plt.plot(timeline, vs)
        plt.xlim(timeline[0], timeline[-1])
        plt.ylim(-0.1, 0.1)
        plt.hlines([0], timeline[0], timeline[-1], colors='r', linestyles='dashed')
        plt.title(f"PID Controller Simulation of Drone Velocity, kp={kp}, ki={ki}, kd={kd}")
        plt.xlabel("Time (s)")
        plt.ylabel("Velocity")
        plt.draw()
        plt.pause(0.01)
        time.sleep(dt)
        i += 1
        if timeline[-1] > 5:
            break
    
    plt.show() # Title the plot before you save!