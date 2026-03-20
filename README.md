# Romi Autonomous Navigation Robot

This project implements an autonomous Romi robot capable of navigating an obstacle course using line-following, obstacle detection, and closed-loop motor control. The robot integrates multiple sensors and a multitasking software architecture to achieve reliable and repeatable performance.

### Project Overview

The robot follows a track using IR reflectance sensors while detecting obstacles with bumper switches. Wheel encoders provide feedback for velocity and position control, and an onboard IMU is used to track orientation during turns. A cooperative multitasking system coordinates line following, motor control, state estimation, and high-level navigation through a finite-state machine.

### Team Members

- Jesse Whitehead  
- Isabel Vega  

### Project Website

<a href="https://JBWhitehead.github.io/Romi-Robot/" target="_blank">
  Full documentation
</a>


### Demo Video

<a href="https://github.com/JBWhitehead/Romi-Robot" target="_blank">
  Romi in action
</a>

### Features

- Line-following using 9-channel IR sensor array  
- Closed-loop motor control using PI controllers  
- Quadrature encoder feedback for velocity and position  
- IMU-based heading estimation  
- Bump sensor detection with interrupt handling  
- Finite-state machine for obstacle course navigation  
- Cooperative multitasking using a custom scheduler  

### Repository Structure

- `main.py` – system initialization, hardware setup, and task creation  
- `motor_control_task.py` – PI control for left and right motors  
- `line_follow_task.py` – line detection and velocity generation  
- `StateEst.py` – state estimation using encoder and IMU data  
- `obstacle_course.py` – high-level FSM for course navigation  
- `bump_int_task.py` – bumper interrupt and debounce handling  
- `motor.py` – motor driver interface  
- `encoder.py` – quadrature encoder interface  
- `sensors.py` – IR sensor processing and centroid calculation  
- `IMU.py` – BNO055 IMU interface  
- `cotask.py` – provided cooperative scheduler  


### System Architecture

The software is organized into modular tasks that communicate through shared variables and queues. A scheduler manages task execution based on priority and timing, while the course task coordinates overall robot behavior.

### Notes

This repository contains all code and supporting files needed to reproduce the project. For detailed explanations, diagrams, and results, please refer to the project website linked above.