"""
Created on Fri Feb  6 12:26:44 2026

@author: Group 25
"""
#-----Imports-----#
from pyb          import Pin, ADC
from motor        import Motor
from encoder      import Encoder
from task_share   import Share, Queue
from micropython  import const
from utime        import ticks_us, ticks_diff

#-----Equates!-----#
S0_INIT = const(0)
S1_WAIT = const(1)
S2_RUN  = const(2)

#-----P Controll-----#
class PI_control_task:
    def __init__(self,
                 mot: Motor, enc: Encoder,
                 goFlag: Share, dataValues: Queue, timeValues: Queue,
                 v_ref: Share, KP: Share, KI: Share, GoLog: Share, u_share: Share, s_share: Share, V_batt: Share):

        self._state = S0_INIT

        self.motor = mot
        self.encoder = enc
        #self.v_batt = 7.2     #change later whith ADC thingy

        # ---- Queues (buffers) ---- #
        self.dataValues = dataValues
        self.timeValues = timeValues
        
        # ---- Shares (flags) ---- #
        self.goFlag = goFlag
        self.GoLog: Share         = GoLog
        self.v_ref: Share  = v_ref
        self.KP: Share = KP
        self.KI: Share = KI
        self.u_share: Share = u_share
        self.s_share: Share = s_share
        
        self.V_batt = V_batt


        # --- PI internals --- #
        self.integral = 0.0 #area under the curve
        self.then = 0#time of prev loop
        self.t0 = 0 #time step response began
        
        # --- Voltage check pin --- #
        self.adc = ADC(Pin.cpu.C0)   # CHANGE WHEN PIN CHOSEN
        
        #let us know
        print("Motor+PI Task object instantiated!")
        
    def read_battery_voltage(self):
        raw = self.adc.read()                 # 0–4095
        v_adc = 3.3 * raw / 4095              # ADC pin voltage
        
        # R1 = 10k, R2 = 4.7k
        v_batt = v_adc * (10_000 + 4_700) / 4_700
        if v_batt < 1:
            v_batt = 1
        
        self.V_batt.put(v_batt)
        
        return v_batt
        

    def run(self):
        '''
        Runs one iteration of the task
        '''
        while True:
            
            #-----S0: INIT ------*
            if self._state == S0_INIT:
                self.V_batt.put(self.read_battery_voltage())
                self._state = S1_WAIT

            #-----S1: Wait for wheel ------*   
            elif self._state == S1_WAIT:
                if self.goFlag.get() == 1:
                    
                    #reset old run
                    self.dataValues.clear()
                    self.timeValues.clear()

                    self.integral = 0.0 #no area under the curve yet
                    
                    self.t0 = ticks_us()
                    self.then = self.t0
                    
                    self.motor.enable() #make sure motor is awake
                    #new state!
                    self._state = S2_RUN

            elif self._state == S2_RUN:
                
                #goodbye then, new now just dropped!!
                now = ticks_us()
                
                #fresh news
                self.encoder.update()
                s = self.encoder.get_position()   
                self.s_share.put(s)           #save the displacement in a little plane traveling to STATEST task
                v_act = self.encoder.get_velocity()
                v_ref = self.v_ref.get()
                KP = self.KP.get()
                KI = self.KI.get()
                
               
                #time stuff
                dt_us = ticks_diff(now, self.then)
                self.then = now

                dt = dt_us * 1e-6 #micro secs to secs
                if dt <= 0:
                    dt = 1e-6

                #calc PI control calcs
                err = v_ref - v_act
                self.integral += err * dt
                eff = (KP * err) + (KI * self.integral)
                
                #get battery current volt and use it as an extra gain
                v_batt = self.read_battery_voltage()
                correction = 7.2 / v_batt
                eff = eff * correction
                
                #update motor from calcs
                self.motor.set_effort(eff)
                
                duty = self.motor.get_last_effort()
                voltage = (duty / 100.0 ) * v_batt   #change hardware driver units of duty% to volts
                self.u_share.put(voltage)     #put in a little plane traveling to STATEST task
                

                #jot down data for plot
                if self.GoLog.get() == 2:
                    elapsed_t = ticks_diff(now, self.t0)*1e-6 #time in sec
                    self.timeValues.put(elapsed_t) #TIME IN Seconds!
                    self.dataValues.put(v_act)
                    
                    if self.timeValues.full() or self.dataValues.full():
                       self.motor.set_effort(0)
                       self.goFlag.put(0)
                       self._state = S1_WAIT
                       self.motor.disable()
                
                if self.goFlag.get() == 0:
                    self.motor.set_effort(0)
                    self.u_share.put(0.0)     #zero voltage share just in case  
                    self._state = S1_WAIT
                    self.motor.disable()

                    
                #we got what we wanted



            yield self._state
