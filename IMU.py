
"""
Created on Sat Mar  7 13:30:13 2026

@author: svega 
"""

#---------------IMU DRIVERRRRRR LETS GET DA PARTY STARTED--------------#
#----------------------------------------------------------------------#
#----------------------------------------------------------------------#



from pyb import I2C
import time



class IMU:
    
    #---Create Class Initialize it 
    #---and pass in i2c channel and reset pin number)
    def __init__(self, i2c_channel, rst_pin):
    
        # ---- REGISTERS ----
        
        # ---- Mode/Chip ----
        self.REG_CHIP_ID    = 0x00
        self.REG_PAGE_ID    = 0x07
        self.REG_OPR_MODE   = 0x3D
        self.REG_PWR_MODE   = 0x3E
        
        # ---- Movement Data ----
        self.REG_ACC_LSB    = 0x08    # 6 bytes
        self.REG_GYRO_LSB   = 0x14    # 6 bytes
        self.REG_EULER_LSB  = 0x1A    # 6 bytes
        self.REG_QUAT_LSB   = 0x20    # 8 bytes
        self.REG_LINACC_LSB = 0x28    # 6 bytes
        self.REG_GRAV_LSB   = 0x2E    # 6 bytes
        
        # ---- Calibration Data ----
        self.REG_CALIB_STAT      = 0x35
        self.REG_COEFF_START     = 0x55
        
        
        # ---- System ----
        self.REG_SYS_STATUS      = 0x39
        self.REG_SYS_ERR         = 0x3A
        self.REG_UNIT_SEL        = 0x3B
        self.REG_SYS_TRIGGER     = 0x3F
        self.REG_AXIS_MAP_CONFIG = 0x41
        self.REG_AXIS_MAP_SIGN   = 0x42
    
        #--------------------#
        
        
        # ---- Constants ----
        self.CHIP_ID_OK  = 0xA0
        self.MODE_CONFIG = 0x00
        self.MODE_IMU    = 0x08      # fusion: accel + gyro only (NO MAG)
        self.PWR_NORMAL  = 0x00
        self.CALIB_LEN   = 22
        #--------------------#
        
        
        # ---- Hardware ----
        self.i2c     = I2C(i2c_channel, I2C.CONTROLLER, baudrate=100000)           # << preconfigured pyb.I2C passed in
        self.addr    = 0x28
        self.rst_pin = rst_pin
        
      
        self.mode = None
        
    # ---------------------------------------------------------------------------
    # Low-level I2C helpers --- Toolbox!! so driver can use these tools everywhere
    #                       --- (reusable functions - reading glasses and pencils)
    # ----------------------------------------------------------------------------
    
    def put(self, val, addr, reg):     
       val = int(val) & 0xFF      
       #mem_write(bytes to send, I2C device addr , register addr inside device) 
       self.i2c.mem_write(bytes([val]), addr, reg) 
       
    #read ONE byte from a register 
    def get_byte(self, addr, reg):
        buf = bytearray(1)
        for attempt in range(5):
            #in a try loop just in case to make sure it does it well
            try:
                self.i2c.mem_read(buf, addr, reg)
                return buf[0]
            except OSError:
                time.sleep_ms(100)
        raise OSError("read8 failed after retries at reg {}".format(hex(reg)))
    
    def get_bytes(self, addr, reg, n): 
       #gets n bytes from reg 
       buffer = bytearray(n) 
       self.i2c.mem_read(buffer, addr, reg) 
       return buffer 
 
    def bits_to_num(self, LSB, MSB): 
       #gets 16bits and converts to signed num 
       num = LSB + (MSB << 8) #shift MSB to become upper half     
       if num & 0x8000: 
           #if true, num is neg 
           num -= 65536        
       return num 
   
    
   
    # ------------------------------------------------------------------ #
    #  Device control / Startup
    # ------------------------------------------------------------------ #
    
    def reset(self):
        """Trigger a system reset via RST pin."""
        self.rst_pin.low()
        time.sleep_ms(50) 
        self.rst_pin.high()
        time.sleep_ms(50)
        
        

    def set_mode(self, mode: int): #Uses blocking code
        """
        Change OPR_MODE:
        - go to CONFIG first, then desired mode
        - datasheet has switching delays, gotta use blocking code ;( 
        """
        mode = int(mode) & 0xFF #ensure its a byte
        
        if self.mode == mode: #dont gotta do anything then
            return
        
        if self.mode != self.MODE_CONFIG: #get into mode_config first ;(
        
            self.i2c.mem_write(bytes([self.MODE_CONFIG]), self.addr, self.REG_OPR_MODE)
            
            time.sleep_ms(30) 
            
            self.mode = self.MODE_CONFIG
            
        self.i2c.mem_write(bytes([mode]), self.addr, self.REG_OPR_MODE)
        
        time.sleep_ms(30) 
                
        self.mode = mode
        
    def begin(self) : #do before scheduler
        """
        Initialize device:
        - verify CHIP_ID
        - reset 
        - set power mode
        - set to IMU mode (NO MAG)
        Return True if detected/configured.
        """
        try:
            
            #reset reset pin
            self.reset()
            
            time.sleep_ms(700)
            
            #varify chip ID
            chip = self.get_bytes(self.addr, self.REG_CHIP_ID, 1)[0] 
            if chip != self.CHIP_ID_OK :
                return False
            
            #wake upppp
            self.put(self.PWR_NORMAL, self.addr, self.REG_PWR_MODE)
            time.sleep_ms(10)
            
            #set the mode
            self.set_mode(self.MODE_IMU)
            
            return True
            
        except Exception as e:
            print(e)
            return False
        
        
        
        
    # ------------------------------------------------------------------ #
    #  Calibration
    # ------------------------------------------------------------------ #
     
    def calib_status_byte(self):
        # --- A method to retrieve the raw calibration status byte 
        # --- from the IMU register CALIB_STAT (0x35)
        return self.get_byte(self.addr, self.REG_CALIB_STAT)
        
        
       
    def calib_status(self):
        # --- parse the calibration status byte from the IMU to look pretty
        b = self.calib_status_byte()      # get the raw data byte from shelf 35
        return {
            "sys":  (b >> 6) & 0x03,      # shift and mask to put each slice into a titled slot
            "gyro": (b >> 4) & 0x03,
            "acc":  (b >> 2) & 0x03,
            "mag":  (b >> 0) & 0x03
        }                                 # return a specified tank thats really
                                          # easy to look in a specific slot
                
                                          
    def read_calib_coeffs(self):
        # --- A method to retrieve the calibration coefficients from the IMU as binary data.
        
        # Save current mode so we can restore it after reading coeffs
        prev_mode = self.mode
    
        # Switch to CONFIG mode real quick
        self.set_mode(self.MODE_CONFIG)
        time.sleep_ms(30)
    
        # Read 22 bytes starting at ACCEL_OFFSET_LSB (0x55)
        coeffs = bytes(self.get_bytes(self.addr, self.REG_COEFF_START, self.CALIB_LEN))
    
        # Restore previous mode
        self.set_mode(prev_mode)
        time.sleep_ms(30)
    
        return coeffs
       
        
           

    def write_calib_coeffs(self, coeff_bytes):

        if len(coeff_bytes) != 22:
            raise ValueError("Calibration data must be 22 bytes.")
    
        prev_mode = self.mode
    
        # Must be in CONFIG mode to write offset registers
        self.set_mode(self.MODE_CONFIG)
        time.sleep_ms(30)
    
        # Write all 22 bytes starting at 0x55
        self.i2c.mem_write(coeff_bytes, self.addr, self.REG_COEFF_START)
    
        # Restore previous mode
        self.set_mode(prev_mode)
        time.sleep_ms(30)   
        # --- A method to write calibration coefficients back to the IMU from pre-recorded binary data
    
    
    
    
    # ------------------------------------------------------------------ #
    #  Data reading
    # ------------------------------------------------------------------ #
    
    def get_accel(self):
       """Raw accel in m/s^2. Available in all fusion modes."""
       b = self.get_bytes(self.addr, self.REG_ACC_LSB, 6)
       return (
           self.bits_to_num(b[0], b[1]) / 100.0,
           self.bits_to_num(b[2], b[3]) / 100.0,
           self.bits_to_num(b[4], b[5]) / 100.0,
       )

    def get_gyro(self):
        """Gyro in deg/s. Available in IMU, NDOF_FMC_OFF, NDOF."""
        g = self.get_bytes(self.addr, self.REG_GYRO_LSB, 6)
        return (
            self.bits_to_num(g[0], g[1]) / 16.0,
            self.bits_to_num(g[2], g[3]) / 16.0,
            self.bits_to_num(g[4], g[5]) / 16.0,
        )

    def get_euler(self):
        """Euler angles (heading, roll, pitch) in degrees. Fusion modes only."""
        e = self.get_bytes(self.addr, self.REG_EULER_LSB, 6)
        return (
            self.bits_to_num(e[0], e[1]) / 16.0,  # heading
            self.bits_to_num(e[2], e[3]) / 16.0,  # roll
            self.bits_to_num(e[4], e[5]) / 16.0,  # pitch
        )

    def get_quaternion(self):
        """Quaternion (w, x, y, z). Fusion modes only."""
        q = self.get_bytes(self.addr, self.REG_QUAT_LSB, 8)
        scale = 1.0 / (1 << 14)
        return (
            self.bits_to_num(q[0], q[1]) * scale,  # w
            self.bits_to_num(q[2], q[3]) * scale,  # x
            self.bits_to_num(q[4], q[5]) * scale,  # y
            self.bits_to_num(q[6], q[7]) * scale,  # z
        )

    def get_linear_accel(self):
        """Linear acceleration in m/s^2 (gravity removed). Fusion modes only."""
        b = self.get_bytes(self.addr, self.REG_LINACC_LSB, 6)
        return (
            self.bits_to_num(b[0], b[1]) / 100.0,
            self.bits_to_num(b[2], b[3]) / 100.0,
            self.bits_to_num(b[4], b[5]) / 100.0,
        )

    def get_gravity(self):
        """Gravity vector in m/s^2. Fusion modes only."""
        b = self.get_bytes( self.addr,self.REG_GRAV_LSB, 6)
        return (
            self.bits_to_num(b[0], b[1]) / 100.0,
            self.bits_to_num(b[2], b[3]) / 100.0,
            self.bits_to_num(b[4], b[5]) / 100.0,
        )
    
    
    
    
    # ------------------------------------------------------------------ #
    #  Outputs
    # ------------------------------------------------------------------ #
    
    def heading(self):
        h, _, _ = self.get_euler()
        return  h


    def yaw_rate(self):
        _, _, gz = self.get_gyro()
        return gz

