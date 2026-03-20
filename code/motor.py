"""
Created on Thu Jan 29 12:29:55 2026

@author: Jesse
"""
#Stuff you can do w/ class
#   motor = Motor(PWM = Pin.cpu.X# , DIR = Pin.cpu.X#, nSLP = Pin.cpu.X#, timer = Timer_Name, channel = #)
#   motor.enable()
#   motor.disable()
#   motor.set_effort(effort)   # -100 to 100 (sign = direction, magnitude = duty%)
#   motor.last_effort

#TL;DR
#   __init__ only configures hardware for *this* motor and leaves it inactive (sleep, 0% PWM)
#   set_effort only controls direction and PWM 
#   enable() wakes the driver into BRAKE mode 
#   disable() puts the driver to sleep 

#-----Imports-----
from pyb import Pin
from pyb import Timer


#-----The class-----
class Motor:
    '''A motor driver interface encapsulated in a Python class. Works with
       motor drivers using separate PWM and direction inputs such as the DRV8838
       drivers present on the Romi chassis from Pololu.'''
    
    def __init__(self, PWM, DIR, nSLP, timer: Timer, channel: int):
        '''Initializes a Motor object'''
        self.nSLP_pin = Pin(nSLP, mode=Pin.OUT_PP, value=0)
        #create and store nslp pin as o/p, and set it as low for safety
        self.DIR_pin = Pin(DIR, mode=Pin.OUT_PP, value=0)
        #create and store direction pin as o/p, and set to low
        self.timer = timer
        #stores existing timer used by motor
        self.pwm = self.timer.channel(channel, pin=Pin(PWM), mode=Timer.PWM, pulse_width_percent=0)
        #Create PWM channel w/ provided info, and start with 0% duty cycle
        self.last_effort = 0
        #stores last used effort
        
    def set_effort(self, effort):
        '''Sets the present effort requested from the motor based on an input value
           between -100 and 100'''
        if effort > 100: #to first get effort in valid range
            effort = 100
        elif effort < -100:
            effort = -100
            
        if effort == 0: 
            self.pwm.pulse_width_percent(0)
            self.last_effort = 0
            return
        
        if effort > 0: #forward or backward depending on sign
            # Forward
            self.DIR_pin.low()
        else:
            # Reverse
            self.DIR_pin.high()
        
        duty = abs(float(effort)) #make effort a float, then get abs value
        
        self.pwm.pulse_width_percent(duty) #set pwm
        
        self.last_effort = effort #update last used effort
        
    def enable(self):
        '''Enables the motor driver by taking it out of sleep mode into brake mode'''
        self.nSLP_pin.high() #wake up
        self.pwm.pulse_width_percent(0)
        self.last_effort = 0
            
    def disable(self):
        '''Disables the motor driver by taking it into sleep mode'''
        self.pwm.pulse_width_percent(0)
        self.nSLP_pin.low() #go to sleep
        self.last_effort = 0
        
    def get_last_effort(self):
        """Return the last effort """
        return self.last_effort
