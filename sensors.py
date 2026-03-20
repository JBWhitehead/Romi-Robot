"""
Sensor classes!!!
Created on Tue Feb 24 10:33:22 2026

@author: Group 25!
"""

# Method TL;DR
#   __init__ only configures hardware for *this* sensor


#-----Imports-----
from pyb import Pin, ADC


#-----The class-----
class Sensor:
    '''A motor driver interface encapsulated in a Python class. Works with
       motor drivers using separate PWM and direction inputs such as the DRV8838
       drivers present on the Romi chassis from Pololu.'''
    
    def __init__(self, left: Pin, mid: Pin, right: Pin, positions_mm=(-4.0, 0.0, 4.0), adc_max=4095):

        self.ADC = [ ADC(Pin(left)), ADC(Pin(mid)), ADC(Pin(right))]
        #turn analog o/p into a digital voltage that nucleo can read
        
        #calibrations
        self.black = [0, 0, 0]
        self.adc_max = adc_max
        self.white = [self.adc_max, self.adc_max, self.adc_max]
        
        #position of sensors on ind. board
        self.pos_mm = list(positions_mm)
        
        #filtering
        self.filtered = [None, None, None]
        
       
        
    def update(self, n = 10): #updates read_filtered
        total = [0,0,0]
        for _ in range(n): #loop for n samples
            
            for i in range(3):  # do for each ch
                total[i] += self.ADC[i].read()
                
            
        for i in range(3):
            
            avg = total[i] / n
            
            self.filtered[i] = avg
               



        
    #----- Return Data ----
    def read_raw(self): #return unfiltered values
        
        return [self.ADC[i].read() for i in range(3)]
    
    def read_filtered(self): #return filtered values
        
        if any(v is None for v in self.filtered):
            return self.read_raw()
        else:
            return self.filtered
        
        
    #----Calibrations----
    def cal_white(self, n = 20): #n = number of samples that will be avaraged
        total = [self.adc_max, self.adc_max, self.adc_max]
        for _ in range(n): #loop for n samples
            raw = self.read_raw() #get data
            for i in range(3):  # do for each ch
                total[i] += raw[i]
                
        self.white = [total[i] / n for i in range(3)]

    def cal_black(self, n = 20):
        total = [0, 0, 0]
        for _ in range(n): #loop for n samples
            raw = self.read_raw() #get data
            for i in range(3):  # do for each ch
                total[i] += raw[i]
                
        self.black = [total[i] / n for i in range(3)]
        
    #----- Get those values between 0 and 1!!!!
    def read_norm(self): #1 is white, 0 is black
        raw = self.read_filtered()
        norm = []
        
        for i in range(3):
            d = self.white[i] - self.black[i]
            
            if d == 0: #no division by zero :((( 
                norm.append(0.0)
                continue
            
            x = (raw[i] - self.black[i])/ d 
       
            #in case things go wrong (prob calibrated wrong)
            if x < 0:
                x = 0.0
            if x > 1:
                x = 1
                
            norm.append(x)
            
        return norm
    
    #----- where is line in respect to center of sensor??
    
    def read_ave(self, invert=True): #invert is for black line following (1 is black, 0 is white)
        norm = self.read_norm()
        
        if invert:
            weight = [1 - x for x in norm]
        else:
            weight = norm
        
        #get weighted ave! (wixi)/wi
        n = 0.0 #xi(wi)
        d = 0.0 #wi
        
        for w, pos in zip(weight, self.pos_mm):
            n += w * pos
            d += w
            
        #no division by zero :((( 
        if d < 1e-6:
            return sum(self.pos_mm)
        
        self.centroid = n/d
        return n/d
    
#wrapper class!!!!
class Sensors: #just does the above, but all at once
    def __init__(self, left: object, mid: object, right: object, positions_mm = (-16.4, -12.4, -8.4, -4.0, 0.0, 4.0, 8.4, 12.4, 16.4)):
        
        self.left  = left
        self.mid   = mid
        self.right = right
        
        self.cent = 0
        
        self.pos_mm = list(positions_mm)
        
        
        
    def update(self): #updates read_filtered

        self.left.update()
        self.mid.update()
        self.right.update()
      
    #read values
    
    def read_raw(self):
        return (self.left.read_raw() + self.mid.read_raw() + self.right.read_raw())
    
    def read_filtered(self):
        return (self.left.read_filtered() +self.mid.read_filtered() + self.right.read_filtered())
    
    def read_norm(self):
        return ( self.left.read_norm() + self.mid.read_norm() + self.right.read_norm())
    
    def cal_black(self, samples=20):
        self.left.cal_black(samples)
        self.mid.cal_black(samples)
        self.right.cal_black(samples)

    def cal_white(self, samples=20):
        self.left.cal_white(samples)
        self.mid.cal_white(samples)
        self.right.cal_white(samples)
        
        
     #----- where is line in respect to center of array??
    def read_ave(self, invert=True): #invert is for black line following (1 is black, 0 is white

       norm = self.read_norm()
       
       if invert:
           weight = [1 - x for x in norm]
       else:
           weight = norm
       
       #get weighted ave! (wixi)/wi
       n = 0.0 #(wixi)
       d = 0.0 #wi
       
       for w, pos in zip(weight, self.pos_mm):
           n += w * pos
           d += w
           
       #no division by zero :((( 
       if d < 1e-6:
           return self.cent

       
       self.cent = n/d
       return n/d
        


