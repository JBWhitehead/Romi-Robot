"""
Created on Sun Mar  1 16:55:30 2026

@author: Group 25

Bumpers!!!!
"""
#-----Imports-----
from pyb    import Pin

#-----Ind Bumper class-----

class Bumper:
    def __init__(self, pin_ID):
        self.pin = Pin(pin_ID, Pin.IN, Pin.PULL_UP)
        
    def pressed(self):
        return self.pin.value() == 0

class Bumpers:
    def __init__(self, BMP0: object, BMP1: object, BMP2: object, BMP3: object, BMP4: object, BMP5: object):
        
        self.right = [BMP2, BMP1, BMP0]
        self.left = [BMP5, BMP4, BMP3]
        self._bumper_list = [BMP0, BMP1, BMP2, BMP3, BMP4, BMP5]
        
            
    def readings(self):
        return { "left":  [b.pressed for b in self.left], "right": [b.pressed for b in self.right]}
            
    
    def left_pressed(self):
        return any(b.pressed() for b in self.left)

    def right_pressed(self):
        return any(b.pressed() for b in self.right)
    
    def any_pressed(self):
        return self.left_pressed() or self.right_pressed()
            