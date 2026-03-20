"""
State estimation!!!

@author: Jess
"""
#-----Imports-----#

#from IMU          import IMU
#from task_share   import Share, Queue
from micropython  import const
from math         import pi, cos, sin 
from ulab         import numpy
#from utime        import ticks_us, ticks_diff

#-----Equates!-----#
S0_INIT = const(0)
S1_WAIT = const(1)
S2_RUN  = const(2)

#-----P Controll-----#
class state_est_task:
    def __init__(self, IMU,
                 #go flag
                 GoEst,
                 #input shares
                 u_port, u_star, s_port, s_star,
                 #output shares
                 psi_share, psiDot_share,
                 xhat0_share, xhat1_share, xhat2_share, xhat3_share,
                 #observer matrices
                 Ad, Bd,
                 #Queues
                 xQ, yQ ):

        self._state = S0_INIT
        
        self.GoEst = GoEst
        self.u_port = u_port
        self.u_star = u_star
        self.s_port = s_port
        self.s_star = s_star
        
        self.psi = psi_share
        self.psiDot = psiDot_share
        
        self.xhat0 = xhat0_share
        self.xhat1 = xhat1_share
        self.xhat2 = xhat2_share
        self.xhat3 = xhat3_share
        
        self.IMU = IMU
        
        #q
        self.xQ = xQ
        self.yQ = yQ
        
        #get the matricies in here
        self.Ad = numpy.array(Ad)
        self.Bd = numpy.array(Bd)
        
        #xhat vec
        self.xhat = numpy.zeros((4, 1))
        print("State estimation task made (⌐■_■)ᕗ ♪♬")
        
    # little helper
    def split_xhat(self):
        self.xhat0.put(float(self.xhat[0, 0])) #s
        self.xhat1.put(float(self.xhat[1, 0])) #psi
        self.xhat2.put(float(self.xhat[2, 0])) #omegaL
        self.xhat3.put(float(self.xhat[3, 0])) #omegaR
        
    def run(self):
        while True:
            #------ S0: INIT ------
            if self._state == S0_INIT:
                
                self.xhat = numpy.zeros((4, 1))
                self.split_xhat()
                self._state = S1_WAIT
                
            #------ S1: Wait ------
            elif self._state == S1_WAIT:
                if self.GoEst.get() == 1:
                    
                    #reset prev run
                    self.xhat = numpy.zeros((4, 1))
                    self.split_xhat()
                    
                    self._state = S2_RUN
            #------ S2: Run ------
            elif self._state == S2_RUN:
                
                #stop when told to stop
                if self.GoEst.get() == 0:
                    self._state = S1_WAIT
                    continue
                
                #open gifts from other tasks 
                uL = float(self.u_port.get())
                uR = float(self.u_star.get())
                sL = float(self.s_port.get())
                sR = float(self.s_star.get())
                
                #deg to radians
                psi = float(self.IMU.heading()) * (pi / 180.0)
                psiDot = float(self.IMU.yaw_rate()) * (pi / 180.0)
                
                #spread the news
                self.psi.put(psi)
                self.psiDot.put(psiDot)
                
                #new vector just dropped
                u_asterisk = numpy.array([[uL],[uR],[sL], [sR], [psi], [psiDot]])
                
                # observer observe time
                self.xhat = numpy.dot(self.Ad, self.xhat) + numpy.dot(self.Bd, u_asterisk)
                #xhat_{k+1} = Ad xhat_k + Bd u*_k
                
                self.split_xhat()
                
                if (not self.xQ.full()) and (not self.yQ.full()):
                    x = self.xhat0.get() * cos(psi)
                    y = self.xhat0.get() * cos(psi)
                    self.xQ.put(x)
                    
                    self.yQ.put(y)
                
            
            yield self._state
            
        

