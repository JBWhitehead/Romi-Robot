"""
Created on Thu Jan 29 14:28:57 2026

@author: Jesse
"""

#--stuff you can do & TL;DR--#

#enc = Encoder(timer_num = #, chA_pin = Pin.cpu.X#, chB_pin = Pin.cpu.X#)
    #makes the encoder object for yo uto refer to later
#enc.update() 
    #updates incoder, will have to do this regularly
#enc.position() & enc.velocity()
    #spit out values
    #can do smth like: print("position:", enc.position(), "velocity:) enc.velocity())

#-----Imports-----#
from pyb import Timer
from time import ticks_us, ticks_diff   # Use to get dt value in update()

#-----The Class-----#
class Encoder:
    '''A quadrature encoder decoding interface encapsulated in a Python class'''

    def __init__(self, timer_num: int , chA_pin, chB_pin):
        '''Initializes an Encoder object'''
        #init for timer and channels!  ( ´◔ ω◔`) ノシ
        self.timer = Timer(timer_num, period = 0xFFFF, prescaler = 0)
        self.timer.channel(1, pin=chA_pin, mode=Timer.ENC_AB)
        self.timer.channel(2, pin=chB_pin, mode=Timer.ENC_AB)
        
        #clearing states
        self.position   = 0     # Total accumulated position of the encoder
        self.prev_count = self.timer.counter()  # Counter value from the most recent update
        self.delta      = 0     # Change in count between last two updates
        self.dt         = 0     # Amount of time between last two updates
        self.then = ticks_us()  # for future dt canculation
        # ^ IDK if defining the first time so much earlier than the first dt calculation would skew the result
    
    
    def update(self): # (☞ﾟ∀ﾟ)☞
        '''Runs one update step on the encoder's timer counter to keep
           track of the change in count and check for counter reload'''
           
        new_count = self.timer.counter() #fetch current timer count     
        delta = new_count - self.prev_count #delta and newcount dont need a "self." because they dont leave the function (local variables)
        
        #16 bit over/under flow correction 
        #changes delta from 0 thru 65536 range to -32768 thru 32767 range
        if delta > 32767: #underflow (motion from 0 to 65536)
            delta -= 65536 
        elif delta < - 32768: #overflow (motion from 65536 to 0)
            delta += 65536 
        #pos delta = forward; neg delta =backward
        
        #store corrected delta and position stuff
        self.position += delta #total position
        self.delta = delta #current delta
        
        #time stuff
        now = ticks_us() #current time
        self.dt = ticks_diff(now, self.then) #get dt
        self.then = now #update last time
        
        self.prev_count = new_count #update prev count
        
    def get_position(self): # (๑•́ ヮ •̀๑)
        '''Returns the most recently updated value of position as determined
           within the update() method'''
        return -self.position * 0.153   #position in mm
            
    def get_velocity(self): # (╯°□°)╯
        '''Returns a measure of velocity using the the most recently updated
           value of delta as determined within the update() method'''
        if self.dt == 0:
            return 0
        self.vel = -self.delta/(self.dt*1e-6)
        return self.vel * 0.153 #convert from enc counts/s to mm/s!
    
    def zero(self):
        '''Sets the present encoder position to zero and causes future updates
           to measure with respect to the new zero position'''
        #clearing states  _(:3」∠)_
        self.position   = 0     # Total accumulated position of the encoder
        self.prev_count = self.timer.counter()  # Counter value from the most recent update
        self.delta      = 0     # Change in count between last two updates
        self.dt         = 0     # Amount of time between last two updates
        self.then = ticks_us()  # for future dt canculation
