
"""
This file contains the U/I task using a class to obtain a left or right wheel value from user

"""

#-----Import-----#

#from pyb            import USB_VCP, UART #USe USB_VCP for Putty, UART for PC
from task_share     import Share, Queue
from micropython    import const

#-----Equates-----#

S0_INIT = const(0) # State 0 - initialiation
S_HUB   = const(17)# Hub state - main menu / wait for char input
S1_SIDE = const(1) # State 1 - - wait for user to input char to determine if step should be for left or right
S2_COL  = const(2) # State 2 - wait for data collection to end
S3_DIS  = const(3) # State 3 - display the collected data

S4_VEL  = const(4) # State 4 - user sets velocity 
S5_GAIN = const(5) # State 5 - user sets KP & KI

S6_LINE = const(6) # State 6 - line following mode!!
S7_TURN = const(7) # State 7 - enter proportonal gain for line following



UI_prompt = ">: "

#-----Class-----#
class user_task:
    '''
    A class that represents a UI task. The task is responsible for reading user
    input over a serial port, parsing the input for single-character commands,
    and then manipulating shared variables to communicate with other tasks based
    on the user commands.
    '''
    def __init__(self, ser, GoPort, GoStar , dataValues, timeValues, v_ref, KP, KI, GoLine, v_star, v_port, line_gain, GoLog, timeQ, centQ):
        
        self._state         = S0_INIT     #creates a state variable that can only be an integer
        
        self._GoPort      = GoPort       # The "go" flag to start data
                                                 # collection from the left                                     # motor and encoder pair
        
        self._GoStar       = GoStar       # The "go" flag to start data
                                                 # collection from the right
                                                 # motor and encoder pair
                                                 
        self._GoLine     = GoLine       # Buffer between user task & line follow
        
        self._ser       = ser          # A serial port object used to
                                                 # read character entry and to
                                                 # print output
                                                 
        self._v_ref         = v_ref        # refrence velocity set by user  
        self._KP            = KP           # Proportional Gain
        self._KI            = KI           # Integral Gain    
        self._v_port         = v_port
        self._v_star         = v_star      
        self._line_gain     = line_gain    # Proportional Gain for line following task               
                                                 
        
        self._dataValues   = dataValues   # A reusable buffer for data
                                                 # collection
        self._timeValues   = timeValues   # A reusable buffer for time
                                                 # stamping collected data
                                                 
        self._vel_buf             = ""           # Buffer to store user-typed velocity characters
        self._kip_buf             = ""
        
        self._GoLog         = GoLog        #Flag to tell when to start/stop logging data for line following
        self._timeQ         = timeQ        # shared Buffer to hold time from line following
        self._centQ         = centQ        #shared buffer to hold centroid data from line following
        
        self._ser.write("User_Task object instantiated!!!  ┬┴┬┴┤(･_├┬┴┬┴  ")
        
    def run(self):
        '''
        Runs one iteration of the task
        '''
        
        while True:
            #-----State 0: INIT -----#    
            if self._state == S0_INIT:        # Init state (can be removed if unneeded)
                self._ser.write("( ˘ ³˘)ノ°ﾟº❍｡ Initializing user task\r\n")
                self._ser.write("Waiting for go command: 'h' for help menu ʕっ•ᴥ•ʔっ \r\n")
                self._ser.write(UI_prompt)
                self._state = S_HUB
                self._kip = 0                 # Flag to determine if need KP or Ki - 0 is KP, 1 is KI
                self._log_mode = 0            # Internal flag to determine what type data collection (S2 and 3)
                self._line_prompted = False    # flag for did line state ask yes or no yet?
                self._KI.put(0.1)
                self._KP.put(0.01)
                self._v_ref.put(100)
                self._line_gain.put(8)
                self._GoLog.put(0)
                                
                
            #-----The Hub: Wait for user input -----#    
            elif self._state == S_HUB: # Wait for UI commands 
                # Wait for at least one character in serial buffer
                if self._ser.any():
                    # Read the character and decode it into a string
                    inChar = self._ser.read(1).decode()
                    if inChar in {"g", "G"}:
                        self._ser.write(f"{inChar}\r\n")
                        self._ser.write("\r\n") 
                        self._ser.write("Waiting for go command: 'p' for port, 's' for starboard\r\n")
                        self._ser.write(UI_prompt)
                        self._state = S1_SIDE
                    elif inChar in {"h", "H"}:
                        self._ser.write(f"{inChar}\r\n")
                        self._ser.write("\r\n") 
                        self._ser.write("+------------------------------------------------------------------------------+\r\n")
                        self._ser.write("| ME 405 Romi Tuning Interface Help Menu  	( * ^ *) ノシ                         |\r\n")
                        self._ser.write("+---+--------------------------------------------------------------------------+\r\n")
                        self._ser.write("| h | Print help menu                                                          |\r\n")
                        self._ser.write("| k | Enter new motor gain values                                              |\r\n")
                        self._ser.write("| v | Choose a new refrence velocity                                           |\r\n")
                        self._ser.write("| p | Enter new line_follow gain                                               |\r\n")
                        self._ser.write("| b | Calibrate black surface                                                  |\r\n")
                        self._ser.write("| w | Calibrate white surface                                                  |\r\n")
                        self._ser.write("| g | Trigger step response and print results                                  |\r\n")
                        self._ser.write("| l | Enter line-follow mode                                                   |\r\n")
                        self._ser.write("+---+--------------------------------------------------------------------------+\r\n")
                        self._ser.write(UI_prompt)
                    elif inChar in {"v", "V"}:
                        self._ser.write(f"{inChar}\r\n")
                        self._ser.write("\r\n") 
                        self._ser.write("Enter a refrence velocity (mm/s):\r\n")
                        self._ser.write(UI_prompt)
                        self._state = S4_VEL
                    elif inChar in {"k", "K"}:
                        self._ser.write(f"{inChar}\r\n")
                        self._ser.write("\r\n") 
                        self._ser.write("Enter proportional gain, KP:\r\n")
                        self._ser.write(UI_prompt)
                        self._state = S5_GAIN
                    elif inChar in {"l", "L"} and self._GoLine.get() == 0:
                        #self._GoLine.put(int(1))  
                        self._line_prompted = False
                        self._ser.write(f"{inChar}\r\n")
                        self._ser.write("\r\n") 
                        #self._ser.write("Press 's' to stop 	( ╥﹏╥) ノシ")
                        self._state = S6_LINE
                        
                    elif inChar in {"b", "B"} and self._GoLine.get() == 0:
                        self._ser.write(f"{inChar}\r\n")
                        self._GoLine.put(int(3))       
                        self._ser.write("Black surface has been calibrated! ᕙ(`▽´)ᕗ\r\n")
                        self._ser.write("--------------------\r\n")
                        self._ser.write("Waiting for next command: 'h' for menu (っ^з^)♪♬ \r\n")
                        self._ser.write(UI_prompt)
                        
                    elif inChar in {"w", "W"} and self._GoLine.get() == 0:
                        self._ser.write(f"{inChar}\r\n")
                        self._GoLine.put(int(7))  
                        self._ser.write("White surface has been calibrated! ᕙ(`▽´)ᕗ\r\n")
                        self._ser.write("--------------------\r\n")
                        self._ser.write("Waiting for next command: 'h' for menu (っ^з^)♪♬ \r\n")
                        self._ser.write(UI_prompt)
                        
                    elif inChar in {"p", "P"}:
                        self._ser.write(f"{inChar}\r\n")
                        self._ser.write("\r\n") 
                        self._ser.write("Enter proportional gain for line following ※\(^o^)/※ :\r\n")
                        self._ser.write(UI_prompt)
                        self._state = S7_TURN
            
            #-----State 1: User picks side -----#    
            elif self._state == S1_SIDE: # Wait for UI commands
                    # Wait for at least one character in serial buffer
                if self._ser.any():
                    # Read the character and decode it into a string
                    
                    inChar = self._ser.read(1).decode()
                    # If the character is an upper or lower case "l", start data
                    # collection on the left motor and if it is an "r", start
                    # data collection on the right motor
                    if inChar in {"l", "L", "p", "P"}:
                        self._ser.write(f"{inChar}\r\n")
                        self._GoPort.put(1)
                        self._log_mode = 1
                        self._GoLog.put(2)
                        self._v_port.put(self._v_ref.get())
                        self._ser.write("Starting left motor loop...\r\n")
                        self._ser.write("Starting data collection...\r\n")
                        self._ser.write("Please wait... \r\n")
                        self._state = S2_COL
                    elif inChar in {"r", "R", "s", "S"}:
                        self._ser.write(f"{inChar}\r\n")
                        self._GoStar.put(1)
                        self._v_star.put(self._v_ref.get())
                        self._log_mode = 1
                        self._GoLog.put(2)
                        self._ser.write("Starting right motor loop...\r\n")
                        self._ser.write("Starting data collection...\r\n")
                        self._ser.write("Please wait... \r\n")
                        self._state = S2_COL
                        
              
            #---------------State 2: Collect Data---------------#       
            elif self._state == S2_COL:

        
                # Decide which "done" condition to use based on _log_mode
                
                # Mode 1: STEP test (velocity) -- original behavior
                if self._log_mode == 1:
                    if self._timeValues.full() or self._dataValues.full():
                        # finished step test
                        self._ser.write("Data collection complete...!!\r\n")
                        self._ser.write("--------------------\r\n")
                        # print the correct header using the stored shares
                        self._ser.write(f"Reference Velocity: {self._v_ref.get()} mm/s\r\n")
                        self._ser.write(f"KP: {self._KP.get()}\r\n")
                        self._ser.write(f"KI: {self._KI.get()}\r\n")
                        self._ser.write("--------------------\r\n")
                        self._ser.write("Time (s), Velocity (mm/s)\r\n")
                        self._GoLog.put(0)
                        self._state = S3_DIS
        
                # Mode 2: LINE logging (centroid)
                elif self._log_mode == 2:
                    
                    if self._timeQ.full() or self._centQ.full():
                        self._GoLine.put(0)   # stop line-follow task
                        self._GoLog.put(0)    # signal logging finished
                        self._GoPort.put(0)
                        self._GoStar.put(0)
                    
                    # logger task should clear _GoLog when finished
                    if self._GoLog.get() == 0:
                        self._ser.write("Line-follow data collection complete...!!\r\n")
                        self._ser.write("--------------------\r\n")
                        self._ser.write("Time (s), Centroid (mm)\r\n")
                        self._state = S3_DIS
        
                # Mode 3: BOTH (velocity + centroid)
               # elif self._log_mode == 3:
                    # wait until all three sources are done
                   # if (not self._GoPort.get()) and (not self._GoStar.get()) and (not self._GoLog.get()):
                    #    self._ser.write("Combined data collection complete...!!\r\n")
                    #    self._ser.write("--------------------\r\n")
                    #    self._ser.write(f"Reference Velocity: {self._v_ref.get()} mm/s\r\n")
                    #    self._ser.write(f"KP: {self._KP.get()}\r\n")
                    #    self._ser.write(f"KI: {self._KI.get()}\r\n")
                    #    self._ser.write("--------------------\r\n")
                    #   self._ser.write("Time (s), Velocity (mm/s), Centroid (mm)\r\n")
                    #   self._state = S3_DIS
        
                # Fallback (if mode==0 or unexpected) -> use motor-only behavior
                else:
                    if (not self._GoPort.get()) and (not self._GoStar.get()):
                        self._ser.write("Data collection complete...!!\r\n")
                        self._ser.write("--------------------\r\n")
                        self._ser.write(f"Reference Velocity: {self._v_ref.get()} mm/s\r\n")
                        self._ser.write(f"KP: {self._KP.get()}\r\n")
                        self._ser.write(f"KI: {self._KI.get()}\r\n")
                        self._ser.write("--------------------\r\n")
                        self._ser.write("Time (s), Velocity (mm/s)\r\n")
                        self._state = S3_DIS
        
            #--------------State 3: Display Data -----------------#  
            elif self._state == S3_DIS:
                # Mode 1: STEP only (velocity)
                if self._log_mode == 1:
                    # while there is data in legacy queues, print time, velocity
                    if self._dataValues.any():
                        self._ser.write("\r\n")
                        self._ser.write(f"{self._timeValues.get()},{self._dataValues.get()},\r\n")
                    else:
                        self._ser.write("\r\n")
                        self._ser.write("--------------------\r\n")
                        self._ser.write("Waiting for go command: 'h' for menu ✌(-‿-)✌ \r\n")
                        self._ser.write(UI_prompt)
                        self._log_mode = 0
                        self._state = S_HUB
            
                # Mode 2: LINE logging (centroid)
                elif self._log_mode == 2:
                    if self._timeQ.any():
                        # pop corresponding items
                        t = self._timeQ.get()
                        c = self._centQ.get() if self._centQ.any() else float('nan')
                        self._ser.write("\r\n")
                        self._ser.write(f"{t},{c},\r\n")
                    else:
                        self._ser.write("\r\n")
                        self._ser.write("--------------------\r\n")
                        self._ser.write("Waiting for go command: 'h' for menu ✌(-‿-)✌ \r\n")
                        self._ser.write(UI_prompt)
                        self._log_mode = 0
                        self._state = S_HUB
            
                # Mode 3: BOTH (velocity + centroid)
                #elif self._log_mode == 3:
                    # While any of the queues has data, pop what we can.
                 #   if self._timeValues.any() or self._timeQ.any():
                        # Prefer synchronized rows: if both time queues exist, use legacy time first
                  #      if self._timeValues.any():
                      #      t = self._timeValues.get()
                   #     elif self._timeQ.any():
                     #       t = self._timeQ.get()
                    #    else:
                       #     t = float('nan')
            
                       # v = self._dataValues.get() if self._dataValues.any() else float('nan')
                       # c = self._centQ.get() if self._centQ.any() else float('nan')
            
                        #self._ser.write("\r\n")
                        #self._ser.write(f"{t},{v},{c},\r\n")
                   # else:
                    #    self._ser.write("\r\n")
                     #   self._ser.write("--------------------\r\n")
                      #  self._ser.write("Waiting for go command: 'h' for menu ✌(-‿-)✌ \r\n")
                       # self._ser.write(UI_prompt)
                        #self._log_mode = 0
                        #self._state = S_HUB
            
                # Fallback: behave like legacy display
                else:
                    if self._dataValues.any():
                        self._ser.write("\r\n")
                        self._ser.write(f"{self._timeValues.get()},{self._dataValues.get()},\r\n")
                    else:
                        self._ser.write("\r\n")
                        self._ser.write("--------------------\r\n")
                        self._ser.write("Waiting for go command: 'h' for menu ✌(-‿-)✌ \r\n")
                        self._ser.write(UI_prompt)
                        self._state = S_HUB

            #-----State 4: User inputs ref velocity-----#  
            elif self._state == S4_VEL:
                if self._ser.any(): #read one char
                    
                    ch = self._ser.read(1)
                    
                    if ch is None or ch == b"": #in case stuff goes wrong
                        pass
                    
                    else:
                        try:
                            c = ch.decode() #convert byte to string
                        except:
                            c = ''           
                        
                        #backspace
                        if c == '\x08' or c == '\x7f': 
                            if len(self._vel_buf) > 0: #check length of buffer
                                self._vel_buf = self._vel_buf[:-1]
                                self._ser.write("\b \b")
                                
                        #user pressed enter! everyone in posotion!!!!
                        elif c == '\r' or c == '\n': 
                        
                            text = self._vel_buf.strip() #fetch buffer
                            self._vel_buf = ""   # reset buffer
                            
                            if text == "":
                                self._ser.write("\r\n") 
                                self._ser.write("No input  :(  Try again:\r\n")
                                self._ser.write(UI_prompt)
                               
                            else:
                                try: #convert into string
                                    self._v_ref.put(float(text))
                                    self._v_port.put(float(text))
                                    self._v_star.put(float(text))
                                    self._ser.write("\r\n") 
                                    self._ser.write("Refrence velocity set (-‿-)\r\n")
                                    self._ser.write("--------------------\r\n")
                                    self._ser.write("Waiting for next command: 'h' for menu (っ^з^)♪♬ \r\n")
                                    self._ser.write(UI_prompt)
                                    self._state = S_HUB
                                    
                                except: #value was not valid
                                    self._ser.write("\r\n") 
                                    self._ser.write("Invalid refrence velocity\r\n")
                                    self._ser.write("Try again:\r\n")
                                    self._ser.write(UI_prompt)                   
                          
                                
                        else: #normal char: add to buff & echo
                            self._vel_buf += c #new character put in buffer
                            self._ser.write(c) #echo that
                            
            #-----State 5: User inputs KP & KI-----#  
            elif self._state == S5_GAIN:
                if self._ser.any(): #read one char
                    
                    ch = self._ser.read(1)
                    
                    if ch is None or ch == b"": #in case stuff goes wrong
                        pass
                    
                    else:
                        try:
                            c = ch.decode() #convert byte to string
                        except:
                            c = ''           
                        
                        #backspace
                        if c == '\x08' or c == '\x7f': 
                            if len(self._kip_buf) > 0: #check length of buffer
                                self._kip_buf = self._kip_buf[:-1]
                                self._ser.write("\b \b")
                                
                        #user pressed enter! everyone in posotion!!!!
                        elif c == '\r' or c == '\n': 
                        
                            text = self._kip_buf.strip() #fetch buffer
                            self._kip_buf = ""   # reset buffer
                            
                            if text == "":
                                self._ser.write("No input  :(  Try again:\r\n")
                                self._ser.write(UI_prompt)
                                
                            else:
                                try: #convert into string
                                    k = float(text)
                                    
                                    if k < 0:
                                        self._ser.write("\r\n") 
                                        if self._kip == 0:           
                                            self._ser.write("Invalid KP, enter a positive number \r\n")
                                        else:
                                            self._ser.write("Invalid KI, enter a positive number \r\n")
                                        self._ser.write("Try again:\r\n")
                                        self._ser.write(UI_prompt) 
                                    else:
                                        self._ser.write("\r\n") 
                                        if  self._kip == 0:
                                            self._KP.put(k)
                                            self._ser.write("KP set :D \r\n")
                                            self._ser.write("--------------------\r\n")
                                            self._ser.write("Enter Integral Gain, KI:\r\n")
                                            self._ser.write(UI_prompt)
                                            self._kip = 1
                                        else:
                                            self._KI.put(k)
                                            self._kip = 0
                                            self._ser.write("KP and KI are set!\r\n")
                                            self._ser.write("--------------------\r\n")
                                            self._ser.write("Waiting for next command: 'h' for menu 	(๑•́ ヮ •̀๑) \r\n")
                                            self._ser.write(UI_prompt)
                                            self._state = S_HUB
                                    
                                except: #value was not valid
                                    self._ser.write("\r\n") 
                                    if self._kip == 0:           
                                        self._ser.write("Invalid KP, enter a positive number \r\n")
                                    else:
                                        self._ser.write("Invalid KI, enter a positive number \r\n")
                                    self._ser.write("Try again:\r\n")
                                    self._ser.write(UI_prompt)
                                    
                        else: #normal char: add to buff & echo
                            self._kip_buf += c 
                            self._ser.write(c)  
                            
             #-----State 6: Romi does line following -----#    
            elif self._state == S6_LINE:

                # Phase 1: ask the question once
                if self._line_prompted == False:
                    self._ser.write("Collect Line Following Data? (y/n)\r\n")
                    self._ser.write(UI_prompt)
                    self._line_prompted = True

                # Phase 2: wait for y/n (or s)
                else:
                    if self._ser.any():
                        inChar = self._ser.read(1).decode()

                        if inChar in {"y", "Y"}:
                            self._ser.write(f"{inChar}\r\n")
                            self._log_mode = 2
                            self._GoLog.put(1)      # start logging 
                            self._GoLine.put(1)     # start line follow 
                            self._GoPort.put(1)
                            self._GoStar.put(1)
                            self._ser.write("Logging centroid...\r\n")
                            self._ser.write(UI_prompt)
                            self._state = S2_COL    # reuse your existing collection pipeline

                        elif inChar in {"n", "N"}:
                            self._ser.write(f"{inChar}\r\n")
                            self._log_mode = 0
                            self._GoLine.put(1)     # start line follow, no logging
                            self._GoPort.put(1)
                            self._GoStar.put(1)
                            self._ser.write("Line following... press 's' to stop.\r\n")
                            self._ser.write(UI_prompt)
                            # stay in S6_LINE

                        elif inChar in {"s", "S"}:
                            self._ser.write(f"{inChar}\r\n")
                            self._GoLine.put(0)
                            self._GoPort.put(0)
                            self._GoStar.put(0)
                            self._log_mode = 0
                            
                            self._ser.write("--------------------\r\n")
                            self._ser.write("Waiting for go command: 'h' for menu ✌(-‿-)✌ \r\n")
                            self._ser.write(UI_prompt)
                            self._line_prompted = False
                            self._state = S_HUB
                    
                        
            #-----State 7: Skip a run -----#    
            elif self._state == S7_TURN:  #to make sure goline buffer is clearedby line task                     
               if self._ser.any(): #read one char
                   
                   ch = self._ser.read(1)
                   
                   if ch is None or ch == b"": #in case stuff goes wrong
                       pass
                   
                   else:
                       try:
                           c = ch.decode() #convert byte to string
                       except:
                           c = ''           
                       
                       #backspace
                       if c == '\x08' or c == '\x7f': 
                           if len(self._vel_buf) > 0: #check length of buffer
                               self._vel_buf = self._vel_buf[:-1]
                               self._ser.write("\b \b")
                               
                       #user pressed enter! everyone in posotion!!!!
                       elif c == '\r' or c == '\n': 
                       
                           text = self._vel_buf.strip() #fetch buffer
                           self._vel_buf = ""   # reset buffer
                           
                           if text == "":
                               self._ser.write("\r\n") 
                               self._ser.write("No input  :(  Try again:\r\n")
                               self._ser.write(UI_prompt)
                              
                           else:
                               try: #convert into string
                                   self._line_gain.put(float(text))
                                   self._ser.write("\r\n") 
                                   self._ser.write("line follow gain set (-‿-)\r\n")
                                   self._ser.write("--------------------\r\n")
                                   self._ser.write("Waiting for next command: 'h' for menu (っ^з^)♪♬ \r\n")
                                   self._ser.write(UI_prompt)
                                   self._state = S_HUB
                                   
                               except: #value was not valid
                                   self._ser.write("\r\n") 
                                   self._ser.write("Invalid reference gain\r\n")
                                   self._ser.write("Try again:\r\n")
                                   self._ser.write(UI_prompt)                   
                         
                               
                       else: #normal char: add to buff & echo
                           self._vel_buf += c #new character put in buffer
                           self._ser.write(c) #echo that
                    
                    
            yield self._state
            
