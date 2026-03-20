"""
Bumper interupt class!!!!
- Purpose of this task is to temporarly disable inturputs to ignore any debounce
- task renables them after a fixed time period
- Interupts run regardless 

Created on Tue Mar 10 10:19:53 2026

@author: Group 25!!!
"""
#-----Imports-----
from task_share     import Queue, Share
from pyb            import ExtInt, Pin, enable_irq, disable_irq
from array          import array

class debounce_jail_task:
    def __init__(self, bumpers:object, bumpQ: Queue, BumpFlag: Share):
        
        #Queue for crash detection
        self._bump_log = bumpQ 
        
        self.BumpFlag = BumpFlag
        self.BumpFlag.put(0)
        
        #Bumpers Object
        self._bumpers = bumpers
        
        #list of each ind bumper (to get bumper pins)
        self._bumper_list = list(self._bumpers._bumper_list)
        
        #dict that associates (ISR line) to (ExtInt object for bumper pin) and (bumper index)
        self._callbacks = {}
        #contains {ISR_line : ExtInt object, bumper ID}

        
        #get (0,BMP0), (1,BMP1).... (5,BMP5)
        for i, bumper in enumerate(self._bumper_list):
        
            #get Pin(Pin.cpu.(Letter)(number),Pin.IN, Pin_PULL_UP) from BMPz
            pin = bumper.pin

            # gets number from pin ID, which corresponds to ISR line
            isr_line = pin.pin() 
            
            #make external interupt object that 
            #object(which pin, trigger, enable pull up risitor, function that runs when interrupt fires)
            Interrupt = ExtInt( pin, ExtInt.IRQ_FALLING , Pin.PULL_UP, self.callback)
    
            #add to dict: dict[key] = value
            self._callbacks[isr_line] = {"ExtInt": Interrupt, "bumperIndex": i}
            


        # Debounce masks:
        self._db_mask = array("H", [0x0000, 0x0000])
        #   _db_mask[0] = current cycle bumps
        #   _db_mask[1] = previous cycle bumps (renable these)
        
    def callback(self,ISR_src): 
        """
        - runs when ExtInt is triggered to disable triggered ISR lines
        """    
        #shift 1 by ISR_src bits to mark which ext int
        self._db_mask[0] |= (1 << ISR_src)

        
        if ISR_src in self._callbacks:
            #disable the ExtInt through the dict
            self._callbacks[ISR_src]["ExtInt"].disable()  
        
            #get bumperID coressponding to ISR line
            bumperID = self._callbacks[ISR_src]["bumperIndex"]
            
            #put triggered bumpers into queue to let other tasks know
            self._bump_log.put(bumperID, in_ISR=True)
            
            self.BumpFlag.put(1) 
        
    

    def run(self):
        """
        - Re-enable any ISR lines that were hit in the *previous* debounce window
        """
        while True:
            # Re-enable any channels due for re-enable (previous mask)
            for isr_line in range(16):
                #scan for any ones in the mask[1]
                if self._db_mask[1] & (1 << isr_line):
                    #check if the ones are in the dict
                    if isr_line in self._callbacks:
                        #re-enable em
                        self._callbacks[isr_line]["ExtInt"].enable()

            #critical selection!!!
            #diable interrupts
            irq_state = disable_irq()
            
            #move mask[0] to mask[1] and clear mask[0]
            self._db_mask[1] = self._db_mask[0]
            self._db_mask[0] = 0x0000
            
            #no more critical selection!!!
            enable_irq(irq_state)

            yield
