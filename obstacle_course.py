"""
Created on Thu Mar 12 10:50:24 2026

@author: Group 25
"""



#-----Import-----#

#from pyb            import USB_VCP, UART #USe USB_VCP for Putty, UART for PC

from micropython    import const
from pyb            import Pin
from math           import pi

#-----Equates-----#

S0_INIT     = const(0)   # State 0  
S1_WAIT     = const(1)   # State 1  
S2_LIN_ST   = const(2)   # State 2  

S3_PARK     = const(3)   # State 3  

S4_CROSS    = const(4)   # State 4  
                                    
                                 
S5_SLALOM   = const(5)   # State 5  

S6_DOT_DIS  = const(6)   # State 6  
S7_WALL_CUP = const(7)   # State 7  

S8_LIN_FIN    = const(8) # State 8    
S9_FINISH  = const(9)   # State 9 


UI_prompt = ">: "



#-----Class-----#
class obstacle_course:
   
    def __init__(self, ser, GoPort, GoStar , dataValues, timeValues, v_ref, KP, KI, GoLine, v_star, v_port, line_gain, GoLog, timeQ, centQ, GoEst, xQ, yQ, s_port, s_star, psi, BumpExtIntQ, white_flag, black_flag, V_batt, BumpFlag):
        
        self._state         = S0_INIT     #creates a state variable that can only be an integer
        
        self.GoPort       = GoPort       # The "go" flag to start data
                                                 # collection from the left                                     # motor and encoder pair
        
        self.GoStar       = GoStar       # The "go" flag to start data
                                                 # collection from the right
                                                 # motor and encoder pair
                                                 
        self.GoLine       = GoLine       # Buffer between user task & line follow
        
        self.GoEst          = GoEst        # Buffer between user task & state estimation      
        
        self._ser           = ser          # A serial port object used to
                                                 # read character entry and to
                                                 # print output
                                                 
        self.v_ref          = v_ref        # refrence velocity set by user  
        self.KP             = KP           # Proportional Gain
        self.KI             = KI           # Integral Gain    
        self.v_port         = v_port
        self.v_star         = v_star      
        self.line_gain      = line_gain    # Proportional Gain for line following task 

        self.s_port         = s_port
        self.s_star         = s_star
        self.psi            = psi
                                                 
        
        self.dataValues    = dataValues   # A reusable buffer for data
                                                 # collection
        self.timeValues    = timeValues   # A reusable buffer for time
                                                 # stamping collected data
                                            
        
        self.GoLog         = GoLog        
        self.timeQ         = timeQ       
        self.centQ         = centQ        
        
        self.xQ            = xQ
        self.yQ            = yQ
        
        self.BumpQ         = BumpExtIntQ
        self.white_flag    = white_flag
        self.black_flag    = black_flag
        self.V_batt        = V_batt
        self.BumpFlag      = BumpFlag
        
        self._button       = Pin(Pin.cpu.C13, Pin.IN) 
        
        self._ser.write("Obstacle_Task object instantiated!!!  ┬┴┬┴┤(･_├┬┴┬┴  \r\n")
       

    # --- Precoded Toolbox: Start and End, Distance and Turn --- #
    
    # --- Go a certain distace, velocities and distance : Start and End --- #
    
    def start_distance(self, v_port_cmd, v_star_cmd):
        # Save starting distance
        self._s_start = float(self.s_star.get())
        
        # Command motors
        self.v_port.put(v_port_cmd)
        self.v_star.put(v_star_cmd)


    def distance_done(self, dist_mm):
        # How far have we moved?
        ds = abs(float(self.s_star.get()) - self._s_start)
        return ds >= float(dist_mm)   
    
    # --- Turn a amount, velocities and distance : Start and End --- #
    def _wrap_pi(self, angle):
        return (angle + pi) % (2 * pi) - pi

    
    def start_turn_abs(self, target_heading, turn_speed=100):
        # Store target
        self._turn_target = float(target_heading)
        
        current = float(self.psi.get())
        error = self._wrap_pi(self._turn_target - current)

        # If we need heading to increase → turn left
        if error > 0:
            self.v_port.put(+turn_speed)   # left wheel backward
            self.v_star.put(-turn_speed)   # right wheel forward
        else:
            self.v_port.put(-turn_speed)   # right turn
            self.v_star.put(+turn_speed)


    def turn_done_abs(self, tol_rad=0.08):
        current = float(self.psi.get())
        error = self._wrap_pi(self._turn_target - current)
        return abs(error) <= tol_rad
    
    def clear_bump_queue(self):
        while self.BumpQ.any():
            self.BumpQ.get()
    
    # --- Stop --- #
    
    def stop_motors(self):
        self.v_port.put(0)
        self.v_star.put(0)
        
        
    # ---------- Actual Course FSM ---------- #       

    def run(self):
        '''
        Runs one iteration of the task
        '''
        
        while True:
            #-----State 0: INIT -----#    
            if self._state == S0_INIT:       
                self._ser.write("( ˘ ³˘)ノ°ﾟº❍｡ Initializing Obstacle Task\r\n")
                self._ser.write("Waiting for go command: 'h' for help menu ʕっ•ᴥ•ʔっ \r\n")            
                self._ser.write(UI_prompt)
                
                self._state = S1_WAIT #change state
                self._state_stage = 0

                #set gains and velocity
                self.KI.put(0.7) 
                self.KP.put(0.003)
                self.v_ref.put(100)
                self.line_gain.put(5)
                
                #clear flags
                self.GoStar.put(0)
                self.GoPort.put(0)
                self.GoLine.put(0)
                self.GoLog.put(0)
                
               
                
                self.GoEst.put(1) #needed to get updated psi and s values

                     
            #----- State_1: Wait for user input -----# 

            elif self._state == S1_WAIT: # Wait for UI commands  
            
                    if self._state_stage == 0: #default start angles 
                         self.start_angle = self.psi.get() 
                         self._state_stage = 1 
                    
                        
                    if self._state_stage == 1: 
                        
                        if self._button.value() == 0: 
                           self._ser.write("Button has been pressed!!! \r\n")   
                           self._state_stage = 0 #reset variable for next state  
                           self._ser.write("Farewell!! ( * ^ *) ノシ  \r\n")  
                           self._state = S2_LIN_ST
                        
                        # Wait for at least one character in serial buffer 
                        if self._ser.any(): 
                            # Read the character and decode it into a string 
                            inChar = self._ser.read(1).decode() 
                            if inChar in {"g", "G"}: 
                                self._ser.write(f"{inChar}\r\n") 
                                self._ser.write("\r\n")  
                                self._state_stage = 0 #reset variable for next state 
                                self._ser.write("Farewell!! ( * ^ *) ノシ  \r\n") 
                                self._state = S2_LIN_ST  
                                 
                            elif inChar in {"b", "B"} and self.GoLine.get() == 0: 
                                self._ser.write(f"{inChar}\r\n") 
                                self.GoLine.put(int(3))        
                                self._ser.write("Black surface has been calibrated! ᕙ(`▽´)ᕗ\r\n") 
                                self._ser.write("--------------------\r\n") 
                                self._ser.write("Waiting for next command: 'h' for menu (っ^з^)♪♬ \r\n") 
                                self._ser.write(UI_prompt) 
                                 
                            elif inChar in {"w", "W"} and self.GoLine.get() == 0: 
                                self._ser.write(f"{inChar}\r\n") 
                                self.GoLine.put(int(7))   
                                self._ser.write("White surface has been calibrated! ᕙ(`▽´)ᕗ\r\n") 
                                self._ser.write("--------------------\r\n") 
                                self._ser.write("Waiting for next command: 'h' for menu (っ^з^)♪♬ \r\n") 
                                self._ser.write(UI_prompt)       
                                 
                            elif inChar in {"p", "P"} and self.GoLine.get() == 0: 
                                self._ser.write(f"{inChar}\r\n")   
                                angle = self.psi.get() 
                                self._ser.write(f"psi = {angle:.3f} rad\r\n")                             
                                self._ser.write("--------------------\r\n") 
                                self._ser.write("Waiting for next command: 'h' for menu (っ^з^)♪♬ \r\n") 
                                self._ser.write(UI_prompt)    
                                 
                            elif inChar in {"z", "Z"} and self.GoLine.get() == 0: 
                                self._ser.write(f"{inChar}\r\n")   
                                self.start_angle = 0                         
                                self._ser.write("Psi has been set! ._.)/\(._. \r\n") 
                                self._ser.write("--------------------\r\n") 
                                self._ser.write("Waiting for next command: 'h' for menu (っ^з^)♪♬ \r\n") 
                                self._ser.write(UI_prompt) 
                                
                            elif inChar in {"v", "V"} and self.GoLine.get() == 0: 
                                self._ser.write(f"{inChar}\r\n")   
                                volt = self.V_batt.get()
                                self._ser.write(f"Battery Voltage = {volt:.3f} Volts\r\n")                             
                                self._ser.write("--------------------\r\n") 
                                self._ser.write("Waiting for next command: 'h' for menu (っ^з^)♪♬ \r\n") 
                                self._ser.write(UI_prompt)
                                 
                            elif inChar in {"h", "H"}: 
                                self._ser.write(f"{inChar}\r\n") 
                                self._ser.write("\r\n")  
                                self._ser.write("+------------------------------------------------------------------------------+\r\n") 
                                self._ser.write("| ME 405 Romi Tuning Interface Help Menu      ( * ^ *) ノシ                        |\r\n") 
                                self._ser.write("+---+--------------------------------------------------------------------------+\r\n") 
                                self._ser.write("| b | Calibrate black surface                                                  |\r\n") 
                                self._ser.write("| w | Calibrate white surface                                                  |\r\n") 
                                self._ser.write("| g | Go!!!!                                                                   |\r\n") 
                                self._ser.write("| p | Check psi                                                                |\r\n") 
                                self._ser.write("| z | Set psi to zero                                                          |\r\n") 
                                self._ser.write("| v | Check battery voltage                                                    |\r\n")
                                self._ser.write("| h | Print help menu                                                          |\r\n") 
                                self._ser.write("+---+--------------------------------------------------------------------------+\r\n") 
                                self._ser.write(UI_prompt) 
                             
            
            # ------ State 2: Line Straight ------ #
            elif self._state == S2_LIN_ST:
               
                # set specific gains
                # self.v_ref.put()    
                # self.KP.put()        
                # self.KI.put()            
                # self.line_gain.put()
               
                # Start line following
                self.GoLine.put(1)
                self.GoPort.put(1)
                self.GoStar.put(1)
                
                if self.white_flag.get() == 1:   
                    self._ser.write("white flag went up")
                    # Line following OFF
                    self.GoLine.put(0)
                    self.stop_motors()
                    self._state_stage = 0
                    self._state = S3_PARK
        
            
            # ------ State 3: Parking Garage ----- #
            elif self._state == S3_PARK:
                
                
                # --- Foward Tiny --- #
                if self._state_stage == 0 and self.GoLine.get() == 88: #make sure line following is in wait stage before beginn
                    
                    # --- Debugging --- #
                    self._ser.write("made it to stage 0 state 3")
                    self._ser.write("DBG S3ST0: psi={:.3f}, v_port={}, v_star={}, GoPort={}, GoStar={}, s_star={:.1f}\r\n".format(
                    float(self.psi.get()), self.v_port.get(), self.v_star.get(),
                    self.GoPort.get(), self.GoStar.get(), float(self.s_star.get())
                    ))
                    
                    self.start_distance(100, 100)   # set speed here
                    self._state_stage = 1
                    self.GoLine.put(0)
                    
                    
                # --- Finish Foward --- #
                elif self._state_stage == 1:
                    
                    if self.distance_done(50):    # <-- set your distance here
                        
                        # --- Debugging --- #
                        self._ser.write("made it to stage 1 state 3")
                        self._ser.write("DBG S3ST1: psi={:.3f}, v_port={}, v_star={}, GoPort={}, GoStar={}, s_star={:.1f}\r\n".format(
                        float(self.psi.get()), self.v_port.get(), self.v_star.get(),
                        self.GoPort.get(), self.GoStar.get(), float(self.s_star.get()),
                        ))    
                        
                        self.stop_motors()
                        self._state_stage = 2
                
                
                # --- Setup First Turn (Right tiny) --- #
                elif self._state_stage == 2:
                    
                    # --- Debugging --- #
                    # Turn right such that we end aligned with 90 right of start heading
                    target_heading = float(1.45)
                    self.start_turn_abs(target_heading, turn_speed=100)
                    
                    # --- Debugging --- #
                    self._ser.write("DBG S3ST2: psi={:.3f}, target={:.3f}, v_port={}, v_star={}, GoPort={}, GoStar={}, s_star={:.1f}\r\n".format(
                    float(self.psi.get()), float(self._turn_target), self.v_port.get(), self.v_star.get(),
                    self.GoPort.get(), self.GoStar.get(), float(self.s_star.get())
                    ))

                    self._state_stage = 3
                    
                # --- Finish First Turn --- #
                elif self._state_stage == 3:
                    
                    if self.turn_done_abs():
                        
                        # --- Debugging --- #
                        #self._ser.write("made it to stage 3 state 3")
                        self._ser.write("DBG S3ST3: psi={:.3f}, target={:.3f}, v_port={}, v_star={}, GoPort={}, GoStar={}, s_star={:.1f}\r\n".format(
                        float(self.psi.get()), float(self._turn_target), self.v_port.get(), self.v_star.get(),
                        self.GoPort.get(), self.GoStar.get(), float(self.s_star.get())
                        ))
                        
                        self.stop_motors()
                        self._ser.write("finished first tiny turn\r\n")
                        self._state_stage = 4
                      
                # --- Foward into Garage --- #
                elif self._state_stage == 4:
                    
                    # --- Debugging --- #
                    self._ser.write("DBG S3ST4: psi={:.3f}, target={:.3f}, v_port={}, v_star={}, GoPort={}, GoStar={}, s_star={:.1f}\r\n".format(
                    float(self.psi.get()), float(self._turn_target), self.v_port.get(), self.v_star.get(),
                    self.GoPort.get(), self.GoStar.get(), float(self.s_star.get())
                    ))
                    
                    self.start_distance(100, 100)   # set speed here
                    self._state_stage = 5
                     
                     
                # --- Finish Foward --- #
                elif self._state_stage == 5:
                    if self.distance_done(80):    # <-- set your distance here
                        
                        # --- Debugging --- #
                        self._ser.write("DBG S3ST5: psi={:.3f}, target={:.3f}, v_port={}, v_star={}, GoPort={}, GoStar={}, s_star={:.1f}\r\n".format(
                        float(self.psi.get()), float(self._turn_target), self.v_port.get(), self.v_star.get(),
                        self.GoPort.get(), self.GoStar.get(), float(self.s_star.get())
                        ))
                        self._ser.write("finished foward into garage\r\n")
                        
                        self.stop_motors()
                        self._state_stage = 6        
                
                # --- Setup 2nd Turn (Right) --- #
                elif self._state_stage == 6:
                    
                    # --- Debugging --- #
                    self._ser.write("DBG S3ST6: psi={:.3f}, target={:.3f}, v_port={}, v_star={}, GoPort={}, GoStar={}, s_star={:.1f}\r\n".format(
                    float(self.psi.get()), float(self._turn_target), self.v_port.get(), self.v_star.get(),
                    self.GoPort.get(), self.GoStar.get(), float(self.s_star.get())
                    ))
                    
                    # Turn right such that we end aligned with 180 right of start heading
                    
                    
                    target_heading = float(self.start_angle + 2.85)
                 
                    self.start_turn_abs(target_heading, turn_speed=100)
                    self._state_stage = 7
                    
                # --- Finish 2nd Turn --- #
                elif self._state_stage == 7:
                    
                    if self.turn_done_abs():
                        
                        # --- Debugging --- #
                        self._ser.write("DBG S3ST7: psi={:.3f}, target={:.3f}, v_port={}, v_star={}, GoPort={}, GoStar={}, s_star={:.1f}\r\n".format(
                        float(self.psi.get()), float(self._turn_target), self.v_port.get(), self.v_star.get(),
                        self.GoPort.get(), self.GoStar.get(), float(self.s_star.get())
                        ))
                        self._ser.write("finished second turn\r\n")
                        
                        self.stop_motors()
                        self._state_stage = 8
                        
                # --- Start Foward To Bump --- #
                elif self._state_stage == 8:
                    self.BumpFlag.put(0)
                    self.clear_bump_queue()
                    self.start_distance(100, 100)   # set speed here
                    self._state_stage = 9   
                   
                # --- Crash then Begin Backup --- #    
                elif self._state_stage == 9: 
                    # if self.BumpQ.any():
                    #     bumped_id = self.BumpQ.get()           # Get the bumper ID (0..5)
                    #     if bumped_id in (2,3): 
                        if self.BumpFlag.get() == 1:
                            self.stop_motors()
                            self.start_distance(-61, -61)   # set speed here
                            self._state_stage = 10 
                            self.BumpFlag.put(0)
                            self.clear_bump_queue()
                            
                # --- Stop Backup --- #        
                elif self._state_stage == 10:
                    ds = abs(float(self.s_star.get()) - self._s_start)
                    
                    self._ser.write("S3ST10: s_star={:.1f}, s_start={:.1f}, ds={:.1f}\r\n".format(
                        float(self.s_star.get()), float(self._s_start), ds))
                    
                    if self.distance_done(15):
                        self._ser.write("finished backing up\r\n")
                        self.stop_motors()
                        self._state_stage = 11   
                
                        
                # --- Setup 3rd Turn (Left) --- #
                elif self._state_stage == 11:
                    
                    # Turn left 90 such that we end aligned with 90 right of the original start heading
                    
                    # --- Debugging --- #
                    self._ser.write("DBG S3ST11: psi={:.3f}, target={:.3f}, v_port={}, v_star={}, GoPort={}, GoStar={}, s_star={:.1f}\r\n".format(
                    float(self.psi.get()), float(self._turn_target), self.v_port.get(), self.v_star.get(),
                    self.GoPort.get(), self.GoStar.get(), float(self.s_star.get())
                    ))
                    
                    target_heading=float(self.start_angle + 1.45)
                    self.start_turn_abs(target_heading, turn_speed=100)
                    self._state_stage = 12
                    
                # --- Finish 3rd Turn (Left 90) --- #
                elif self._state_stage == 12:
                    
                    if self.white_flag.get() == 0:   
                        self._ser.write("white flag went down")
                        # Line following ON
                        self.GoLine.put(1)
                        #self.stop_motors()
                        self._s_start = float(self.s_star.get())
                        self._state_stage = 0
                        self._state = S4_CROSS 
                
                
                
            # ------ State 4: Cross and Cup ------ #
            elif self._state == S4_CROSS:
                
                # --- Get to Cross (200mmish) --- #
                if self._state_stage == 0:
                    
                    if self.distance_done(267):    # <-- set your distance here
                        self._ser.write("finished foward out of garage to cross\r\n")    
                        self.stop_motors()
                        self.GoLine.put(0)
                        self._state_stage = 1

                # --- Setup First Turn (Left 90) --- #
                elif self._state_stage == 1 and self.GoLine.get() == 88:
                    
                    # --- Debugging --- #
                    self._ser.write("DBG S4ST1: psi={:.3f}, target={:.3f}, v_port={}, v_star={}, GoPort={}, GoStar={}, s_star={:.1f}\r\n".format(
                    float(self.psi.get()), float(self._turn_target), self.v_port.get(), self.v_star.get(),
                    self.GoPort.get(), self.GoStar.get(), float(self.s_star.get())
                    ))
                    
                    # Turn left 90 such that we end aligned with the original start heading
                    self.start_turn_abs(target_heading=float(0.3), turn_speed=60)
                    self._state_stage = 2
                    
                # --- Finish First Turn (Left 90) --- #
                elif self._state_stage == 2:
                    
                    if self.turn_done_abs():
                        # --- Debugging --- #
                        self._ser.write("DBG S4ST2: psi={:.3f}, target={:.3f}, v_port={}, v_star={}, GoPort={}, GoStar={}, s_star={:.1f}\r\n".format(
                        float(self.psi.get()), float(self._turn_target), self.v_port.get(), self.v_star.get(),
                        self.GoPort.get(), self.GoStar.get(), float(self.s_star.get())
                        ))
                        self._ser.write("finished first turn, now facing cup\r\n")
                        #self.stop_motors()
                        #self.v_ref.put(50)
                        #self.GoLine.put(1)
                        self._state_stage = 3
                    
                # --- Foward Push Cup --- #
                elif self._state_stage == 3:
                #     if self.white_flag.get() == 1:
                #         self.stop_motors()
                #         self.GoLine.put(0)
                #         #self.v_ref(100)
                #         self._state_stage = 18
                
                # elif self._state_stage == 18 and self.GoLine.get() == 88:
                                        
                    self.start_distance(100, 100)   # set speed here 
                    self._state_stage = 4
                    
                # --- Finish Foward --- #
                elif self._state_stage == 4:
                    if self.distance_done(342):    # <-- set your distance here
                        self._ser.write("finished pushing cup\r\n")
                        self.stop_motors()
                        self._state_stage = 5
                    
                # --- Reverse to Line --- #
                elif self._state_stage == 5:
                    self.start_distance(-100, -100)   # set speed here
                    self._state_stage = 6
                    
                # --- Finish Reverse --- #
                elif self._state_stage == 6:
                    if self.distance_done(342):    # <-- set your distance here
                        self._ser.write("finished reversing\r\n")    
                        self.stop_motors()
                        self._state_stage = 7
                
                
                # --- Setup Turn Back (Right) --- #
                elif self._state_stage == 7:
                    
                    # Turn right 90 such that we end aligned with 90 right of the original start heading
                    
                    # --- Debugging --- #
                    self._ser.write("DBG S4ST7: psi={:.3f}, target={:.3f}, v_port={}, v_star={}, GoPort={}, GoStar={}, s_star={:.1f}\r\n".format(
                    float(self.psi.get()), float(self._turn_target), self.v_port.get(), self.v_star.get(),
                    self.GoPort.get(), self.GoStar.get(), float(self.s_star.get())
                    ))
                    
                    target_heading=float(self.start_angle + 1.45)
                    self.start_turn_abs(target_heading, turn_speed=60)
                    self._state_stage = 8
                    
                # --- Finish Turn Back (Right 90) --- #
                elif self._state_stage == 8:
                    
                    if self.psi.get() >=1 and self.psi.get() <=2 and self.white_flag.get() == 0:   
                        self._ser.write("white flag went down")
                        # Line following ON
                        self.v_ref.put(50)
                        self.GoLine.put(1)
                        self._state_stage = 9
               
                
                # --- Get to Corner (line follow) --- #
                elif self._state_stage == 9:
                    
                    if self.white_flag.get() == 1:    
                        self._ser.write("finished foward to corner\r\n")    
                        self.stop_motors()
                        self.GoLine.put(0)
                        self._state_stage = 10
                  

                # --- Setup Last Turn (Right 90) --- #
                elif self._state_stage == 10 and self.GoLine.get() == 88:
                    
                    # --- Debugging --- #
                    self._ser.write("DBG S4ST10: psi={:.3f}, target={:.3f}, v_port={}, v_star={}, GoPort={}, GoStar={}, s_star={:.1f}\r\n".format(
                    float(self.psi.get()), float(self._turn_target), self.v_port.get(), self.v_star.get(),
                    self.GoPort.get(), self.GoStar.get(), float(self.s_star.get())
                    ))
                    
                    # Turn right 90 such that we end aligned with 180 of the original start heading
                    self.start_turn_abs(target_heading=float(self.start_angle + 2.92), turn_speed=60)
                    self._state_stage = 11
                
                # --- Finish Last Turn (Right 90) --- #
                elif self._state_stage == 11:
                    
                    if self.white_flag.get() == 0:   
                        self._ser.write("white flag went down")
                        # Line following ON
                        self._state_stage = 0
                        self.line_gain.put(5)
                        self.v_ref.put(100)
                        self.GoLine.put(1)
                        self._state = S5_SLALOM
                        
                   
            # ------ State 5: Line Squiggle ------ #
            elif self._state == S5_SLALOM:
                
               
                if self.psi.get() >= 6 and self.white_flag.get() == 1:   
                    self._ser.write("white flag went up and heading correct")
                    
                    # Line following OFF
                    self._state_stage = 0
                    #self.GoLine.put(0)
                    self.line_gain.put(2.5)
                    self._s_start = float(self.s_star.get())
                    # self.stop_motors()
                    self._state = S6_DOT_DIS
               
                
            
            # ----- State 6: Dotted Distance ----- #
            elif self._state == S6_DOT_DIS:
             
                if self.distance_done(400):    # <-- set your distance here
                    self._ser.write("finished dotted line\r\n")
                    self.stop_motors()
                    self._state_stage = 0
                    self.GoLine.put(0)
                    self._state = S7_WALL_CUP 
               
                
               
            # ------ State 7: Get Wall Cup ------- #
            elif self._state == S7_WALL_CUP:
                
                # --- Turn Right --- #
                if self.GoLine.get() == 88 and self._state_stage == 0:
                    
                    self.start_turn_abs(target_heading=float(1.15), turn_speed=100)
                    self._state_stage = 1
                    
                # --- Finish Turn 1 --- #
                elif  self._state_stage == 1:
                    
                    if self.turn_done_abs():
                        self.start_distance(100, 100)
                        self._state_stage = 2
                            
                # --- Turn Left --- #    
                elif self._state_stage == 2:
                    
                    if self.distance_done(90):
                        self.start_turn_abs(target_heading=float(0.2), turn_speed=100)
                        self._state_stage = 3
                
                # --- Foward Until Bump --- #
                elif self._state_stage == 3:
                    
                    if self.turn_done_abs():
                        self.BumpFlag.put(0)
                        self.clear_bump_queue()
                        self.start_distance(100, 100)
                        self.clear_bump_queue() 
                        self._state_stage = 4
                
                # --- Bump Begin Backup --- #
                elif self._state_stage == 4: 
                    # if self.BumpQ.any():
                    #     bumped_id = self.BumpQ.get()           # Get the bumper ID (0..5)
                    #     if bumped_id in (2,3): 
                    if self.BumpFlag.get() == 1:
                        self.stop_motors()
                        self.start_distance(-61, -61)   # set speed here
                        self._state_stage = 5 
                        self.BumpFlag.put(0)
                            
                # --- Finish Backup --- #
                elif self._state_stage == 5:
                    
                    if self.distance_done(15):
                        self.start_turn_abs(target_heading=float(5), turn_speed=100)
                        self._state_stage = 6   
                
                # --- Push Cup --- #
                elif self._state_stage == 6:
                    
                    if self.turn_done_abs():
                        self.start_distance(100, 100)
                        self._state_stage = 7   
                
                # --- To Line --- #
                elif self._state_stage == 7:
                    
                    if self.distance_done(430):
                        self.start_turn_abs(target_heading=float(3.2), turn_speed=100)
                        self._state_stage = 0
                        self._state = S8_LIN_FIN 
                        
                        
            # ------- State 8: Lne Until Finish ------ #
            
            elif self._state == S8_LIN_FIN:
                
                if self.white_flag.get() == 0:
                    self._ser.write("white flag went down\r\n")
                    
                    # Line following ON
                    self._state_stage = 0
                    self.GoLine.put(1)
                    self.line_gain.put(5)
                    self._state = S9_FINISH  
                    
                    
            
            # ------- State 9: Take a Bow ------- #
            elif self._state == S9_FINISH:
                
                if self._state_stage == 0:
                    if self.white_flag.get() == 1:
                        self._ser.write("white flag went up\r\n")
                        
                        # Line following OFF
                        self._state_stage = 1
                        self.stop_motors()
                        self.GoLine.put(0)
                        
                
                elif self._state_stage == 1 and self.GoLine.get() == 88:
                    
                    self.start_distance(100, 100)
                    self._state_stage = 2
                    
                    
                elif self._state_stage == 2:
                        if self.distance_done(115):
                            self._ser.write("CHECKPOINT 5 LETS GOOOOOOO!!!!\r\n")
                            self.start_turn_abs(target_heading=float(0.5), turn_speed=500)
                            self._state_stage = 3
                     
                elif self._state_stage == 3:
                    
                    if self.distance_done(1150):
                        self.stop_motors()
                        self._ser.write("YIPPPEEEEEEE!!!!\r\n")
                        self._state_stage = 1
                        self._state = S1_WAIT
            
            
            yield self._state 