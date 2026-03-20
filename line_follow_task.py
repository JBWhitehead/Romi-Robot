# -*- coding: utf-8 -*-
"""
Created on Tue Feb 24 15:43:14 2026

@author: Group 25
"""

#-----Import-----#
from micropython    import const
from task_share     import Share, Queue
import utime

#check the logmode flag, collect data for log_flag ==2
#-----Equates-----#

S0_INIT  = const(0) # State 0 - initialiation
S1_WAIT  = const(1) # State 1 - wait for share from user task
S2_LINE  = const(2) # State 2 - follow that line!

#-----Class-----#
class line_follow_task:
    """
    Line-following task:
    - Waits for UI commands through GoLine share
    - Calibrates sensors on 'b' (black) and 'w' (white)
    """
    def __init__(self, sensors: object, GoLine: Share, v_ref: Share, v_star: Share, v_port: Share,
                 gain: Share, GoLog: Share, timeQ: Queue, centQ: Queue, white_flag: Share, black_flag: Share, middle = 0):
        # state
        self._state = S0_INIT

        # driver objects and shares
        self.sensors = sensors
        self.GoLine = GoLine #share b/w user

        # These are Shares: use get()/put()
        self.v_ref = v_ref
        self.v_star = v_star
        self.v_port = v_port
        self.gain = gain
        self.white_flag = white_flag
        self.black_flag = black_flag
        
        #queues and things to talk to the user task
        self.GoLog = GoLog
        self.timeQ = timeQ
        self.centQ = centQ
        self._t0 = utime.ticks_ms()

        # center point (mm) and threshold for entering turning states
        self.middle_mm = float(middle)
        
        #let us know
        print("Line-Following Task has been instantiated!")
    
    #little function to check the readings and see if were getting mostly white
    def mostly_white(self):
        #self.sensors.update()
        reading = self.sensors.read_norm() 
        
        for val in reading:
            if val <= 0.9:
                return False
                
        return True
    
    def mostly_black(self):
        #self.sensors.update()
        reading = self.sensors.read_norm() 
        
        for val in reading:
            if val >= 0.3:
                return False
                
        return True
        
    def run(self):
        '''
        Runs one iteration of the task
        '''
        
        while True:
            #-----State 0: INIT -----#
            if self._state == S0_INIT: # Init state (can be removed if unneeded)
                self.GoLine.put(int(0))
                try:
                    #is v ref already populated?
                    self.v_star.put(self.v_ref.get())
                    self.v_port.put(self.v_ref.get())
                except Exception:
                    #if not
                    self.v_star.put(0)
                    self.v_port.put(0)
                self._state = S1_WAIT

                
            #-----State 1: Wait-----#
            elif self._state == S1_WAIT: 
                Next = self.GoLine.get()
                self.sensors.update() # update to not skip line following
                
                # --- Set up white flag if it hits mostly white ---- #
                if self.mostly_white() == True:
                    self.white_flag.put(1)
                else:
                    self.white_flag.put(0)
                
                if Next == 3:
                    self.sensors.cal_black(30)
                    self.GoLine.put(0) #clear share
                    
                elif Next == 7:
                    self.sensors.cal_white(30)
                    self.GoLine.put(0)
                    
                elif Next ==1:
                    # start line following (you would transition to a RUN state)
                    self._t0 = utime.ticks_ms()   # <-- add this line (reset time at start)
                    # vref_val = self.v_ref.get()
                    # self.v_star.put(vref_val)
                    # self.v_port.put(vref_val)
                    self._state = S2_LINE
                    self.timeQ.clear()
                    self.centQ.clear()
                    
                    
            #-----State 2: Run-----#
            elif self._state == S2_LINE: 
                #new data!!
                self.sensors.update()
                
                
                # --- Set up white flag if it hits mostly white ---- #
                if self.mostly_white() == True:
                    self.white_flag.put(1)
                else:
                    self.white_flag.put(0)
                
                # --- Set up black flag if it hits mostly black ---- #
                if self.mostly_black() == True:
                    self.black_flag.put(1)
                else:
                    self.black_flag.put(0)
                
                centroid = float(self.sensors.read_ave()) # centroid in mm
                
                # log centroid vs time if enabled
                if self.GoLog.get() == 1:
                    # stop cleanly if full BEFORE put() can block
                    if self.timeQ.full() or self.centQ.full():
                        self.GoLog.put(0)
                        self.v_port.put(0)
                        self.v_star.put(0)
                        self._state = S1_WAIT
                    else:
                        t = utime.ticks_diff(utime.ticks_ms(), self._t0) / 1000.0
                        self.timeQ.put(t)
                        self.centQ.put(centroid)
                    
                # compute error relative to center point
                error_mm = centroid - self.middle_mm  #pos if centroid is right, neg if centroid is left
                    
                delta = self.gain.get() * error_mm  
                


                
                #tuning time!!
                vref = self.v_ref.get()
                
                #clamp delta 
                if delta > vref:
                    delta = vref
                elif delta < -vref:
                    delta = -vref
                
                #calc new velocity
                v_left = vref + delta
                v_right = vref - delta
                
                # so v can never be larger than vmax
                vmax = max(abs(vref) * 2, 20.0)
                if v_left > vmax:  v_left = vmax
                if v_left < -vmax: v_left = -vmax
                if v_right > vmax:  v_right = vmax
                if v_right < -vmax: v_right = -vmax
                
                #so v can never be smaler than vmin
                vmin = 20.0

                if vref >= 0:
                    if v_left  < vmin: v_left  = vmin
                    if v_right < vmin: v_right = vmin
                else:
                    if v_left  > -vmin: v_left  = -vmin
                    if v_right > -vmin: v_right = -vmin
                
                # send the values to motor driver
                self.v_port.put(v_left)
                self.v_star.put(v_right)                   

                #time to stop
                if self.GoLine.get() == 0:
                    self.v_port.put(0)
                    self.v_star.put(0)
                    self.GoLine.put(88)
                    self._state = S1_WAIT
      
                    
                

                                                        
            yield self._state
        
        
        


