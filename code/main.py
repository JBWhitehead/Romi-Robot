"""
Created on Thu Feb  5 12:10:45 2026

 	~=[,,_,,]:3
     
 Mecha25
"""
#USerial Port!!!
from pyb import UART, repl_uart, USB_VCP

from obstacle_course    import obstacle_course

#ser = UART(5, 115200)     # MUST match your HC-05 baud
#repl_uart(ser)      # move REPL to Bluetooth UART
ser = USB_VCP() #when working only on PUTTY #baude 11520



#-----Import Tasks-----#
from task_share         import Share, Queue, show_all
from cotask             import Task, task_list
#from user_task          import user_task
from motor_control_task import PI_control_task
from line_follow_task   import line_follow_task
from StateEst           import state_est_task

from bump_int_task      import debounce_jail_task

#-----Equates-----#

w = 500 #p redundant unless you forget to calibrate
m = 0

#Ad must be 4x4
Ad = [
    [ 0.7427,  0.0000,  0.2494,  0.2494],
    [ 0.0000,  0.0061,  0.0000,  0.0000],
    [-0.1212,  0.0000,  0.3192,  0.3095],
    [-0.1212,  0.0000,  0.3095,  0.3192]
]


#Bd must be 4x6
Bd = [
    [0.1962, 0.1962, 0.1287, 0.1287, -0.0000, -0.0000],
    [0.0000, 0.0000, -0.0071, 0.0071,  0.0001,  0.0039],
    [0.7137, 0.4156, 0.0606, 0.0606, -0.0000, -1.8098],
    [0.4156, 0.7137, 0.0606, 0.0606, -0.0000,  1.8098]
]


#-----Hardware/Timer Objects-----#

#-----Import Files-----#
from pyb          import Pin, Timer
from motor        import Motor
from encoder      import Encoder




#Timers ┻━┻ ︵ヽ(`Д´)ﾉ︵ ┻━┻
tim1 = Timer(1, freq=20000)

#motors ٩( ๑╹ ꇴ╹)۶
motor_port = Motor(PWM=Pin.cpu.A9, DIR=Pin.cpu.A8, nSLP=Pin.cpu.B2, timer=tim1, channel=2)
motor_star = Motor(PWM=Pin.cpu.A10, DIR=Pin.cpu.C4, nSLP=Pin.cpu.A2, timer=tim1, channel=3)

#encoders  ƪ(ړײ)ƪ​​
enc_port = Encoder(timer_num = 2, chA_pin = Pin.cpu.A0, chB_pin= Pin.cpu.A1)
enc_star = Encoder(timer_num = 3, chA_pin = Pin.cpu.B4, chB_pin= Pin.cpu.B5)

from sensors      import Sensor, Sensors
#sensors ノ┬─┬ノ ︵ ( \o°o)\
sen_left  = Sensor(left=Pin.cpu.B1, mid=Pin.cpu.C3, right=Pin.cpu.C2, positions_mm=(-4.0, 0.0, 4.0), adc_max = w)
sen_mid   = Sensor(left=Pin.cpu.C1, mid=Pin.cpu.B0, right=Pin.cpu.A4, positions_mm=(-4.0, 0.0, 4.0), adc_max = w)
sen_right = Sensor(left=Pin.cpu.A7, mid=Pin.cpu.A6, right=Pin.cpu.C5, positions_mm=(-4.0, 0.0, 4.0), adc_max = w)

sensors = Sensors(left = sen_left, mid = sen_mid, right = sen_right, positions_mm=(-17.0 , -13.0 , -9.0, -4.0, 0.0, 4.0, 9.0, 13.0, 17.0))

from bumpers      import Bumper, Bumpers
#Bump Sensors

bump_0 = Bumper(Pin.cpu.B13)
bump_1 = Bumper(Pin.cpu.B14)
bump_2 = Bumper(Pin.cpu.B11)
bump_3 = Bumper(Pin.cpu.H0)
bump_4 = Bumper(Pin.cpu.H1)
bump_5 = Bumper(Pin.cpu.A15)

bumpers = Bumpers(BMP0 = bump_0, BMP1 = bump_1, BMP2 = bump_2, BMP3 = bump_3, BMP4 = bump_4, BMP5 = bump_5)

#bump interrupt Q

BumpExtIntQ  = Queue("B", 6, name="Triggered Bump Sensor Buffer") # B is uint8

from IMU          import IMU
#IMU
rst_pin = Pin(Pin.cpu.C11, Pin.OUT_PP, value=1) #starts high 
imu = IMU(1, rst_pin) 
imu_ok = imu.begin() 
if not imu_ok: 
    print("WARNING: IMU begin() failed; check wiring / power / I2C channel.") 

try: 
    with open("imu_cal.bin", "rb") as f: 
        coeffs = f.read(22) 
    imu.write_calib_coeffs(coeffs) 
    print("IMU calibration loaded from imu_cal.bin") 
except OSError: 
    print("No saved IMU calibration file found (imu_cal.bin).") 


#------Shares(pass around) & Queues (conveyor belt) -----#   

GoPort        = Share("B",      name="Port Motor's Go Flag")       # B is for 8-bit unsigned int
GoStar        = Share("B",      name="Starboard Motor's Go Flag")
GoLine        = Share("B",      name="Line-following Buffer")                #data from user task to line follow ta
GoEst         = Share("B",      name="State Estimation Buffer")

white_flag    = Share("B",      name= "Line following sees mostly white")
black_flag    = Share("B",      name= "Line following sees mostly white")

KP            = Share("f",      name="Proportional Gain")          # f is for float
KI            = Share("f",      name="Integral Gain")              # f is for float
v_ref         = Share("f",      name="Refrence Velocity")          # f is for float
v_port        = Share("f",      name="Port Refrence Velocity")     # f is for float
v_star        = Share("f",      name="Star Refrence Velocity")     # f is for float
KP_line       = Share("f",      name="Line-Follow Proportional Gain")          # f is for float

# Inputs to estimator
s_port        = Share("f",      name="Port Displacement in mm")     # f is for float
s_star        = Share("f",      name="Star Displacement in mm")     # f is for float
u_port        = Share("f",      name="Port Motor Input Voltage")     # f is for float
u_star        = Share("f",      name="Star Motor Input Voltage")     # f is for float

V_batt        = Share("f",      name="Romi Battery Voltage")     # f is for float

BumpFlag      = Share("B",      name="Bumper Hit")

# IMU outputs
psi = Share("f", name="Yaw - psi (rad)")
psiDot = Share("f", name="Yaw rate - psiDot (rad/s)")

# Estimated state outputs 
xhat0 = Share("f", name="xhat[0]")
xhat1 = Share("f", name="xhat[1]")
xhat2 = Share("f", name="xhat[2]")
xhat3 = Share("f", name="xhat[3]")


#step test
dataValues    = Queue("f", 5, name="Data Collection Buffer")     # f is for float, "30" is num of items queue can hold
timeValues    = Queue("f", 5, name="Time Buffer")                # L is for 32-bit unsigned int

# new: logging share + queues for centroid logging
GoLog        = Share("B",      name="Line Logging Flag")         # 1 while logging, 0 when done
timeQ_line   = Queue("f", 5, name="Line Time Buffer")         # time samples for line logging
centQ        = Queue("f", 5, name="Centroid Buffer")          # centroid samples for line logging

xQ         = Queue("f", 5, name="Psi Buffer")
yQ      = Queue("f", 5, name="Psi_dot Buffer")



#-----Task Objects-----#

#UserTask            = user_task(ser, GoPort, GoStar , dataValues, timeValues, v_ref, KP, KI, GoLine, v_star, v_port, KP_line, GoLog, timeQ_line, centQ, GoEst, xQ, yQ)

PortControlTask     = PI_control_task(motor_port, enc_port, GoPort, dataValues, timeValues, v_port, KP, KI, GoLog, u_port, s_port, V_batt)

StarControlTask     = PI_control_task(motor_star, enc_star, GoStar, dataValues, timeValues, v_star, KP, KI, GoLog, u_star, s_star, V_batt)

SensorTask          = line_follow_task(sensors, GoLine, v_ref, v_star, v_port, KP_line, GoLog, timeQ_line, centQ, white_flag, black_flag, m)

StateEstTask        = state_est_task(imu, GoEst, u_port, u_star, s_port, s_star, psi, psiDot, xhat0, xhat1, xhat2, xhat3, Ad, Bd, xQ, yQ )

CourseTask         = obstacle_course(ser, GoPort, GoStar, dataValues, timeValues, v_ref, KP, KI, GoLine, v_star, v_port, KP_line, GoLog, timeQ_line, centQ, GoEst, xQ, yQ, s_port, s_star, psi, BumpExtIntQ, white_flag, black_flag, V_batt, BumpFlag)

DebounceJailTask = debounce_jail_task(bumpers, BumpExtIntQ, BumpFlag)




#-----Adding Tasks to Scheduler-----#

task_list.append(Task(PortControlTask.run, name="Port's Closed Loop Control Task",
                      priority = 3, period = 50, profile=True))

task_list.append(Task(StarControlTask.run, name="Starboard's Closed Loop Control Task",
                      priority = 3, period = 50, profile=True))

# task_list.append(Task(UserTask.run, name="User Interface Task",
#                       priority = 0, period = 100, profile=True))

task_list.append(Task(SensorTask.run, name="Line-Following Task",
                     priority = 2, period = 50, profile= True))

task_list.append(Task(StateEstTask.run, name="State Estimation Task",
                     priority = 1, period = 50, profile= True))

task_list.append(Task(DebounceJailTask.run, name="Bumper External Interrupt Task",
                      priority = 4, period = 400, profile=True))

task_list.append(Task(CourseTask.run, name="Course Task",
                     priority = 0, period = 0, profile= True))

#------Loop-----#
while True:
    try:
        task_list.pri_sched()

        
    except KeyboardInterrupt:
        print("Program Terminating 	(ง ͠° ͟ʖ ͡°)ง")
        motor_star.disable()
        motor_port.disable()
        break

print("\n")
print(task_list)
print(show_all())




