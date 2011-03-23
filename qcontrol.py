#!/usr/bin/python

import socket
import select
import io
import time
import serial

class Nas:
  """
  QNAP has published their GPL image code

  get the source from:
  
  hostname: ftp.qnap.com
  login: gpl
  password: download
  
  most of this is cribbed from src/linux-2.6.33.2/include/qnap/ 
  from that distribution
  
  """
  command = {}

  status = {}    
  status[0x74] 	 	= "FAN1_NORMAL"
  status[0x75]		= "FAN2_NORMAL"
  status[0x76]		= "FAN2_ERROR"	
  status[0x77]		= "FAN3_NORMAL"
  status[0x78]		= "FAN3_ERROR"	
  status[0x79] 		= "FAN4_NORMAL"
  status[0x80] 		= "FAN4_ERROR"	


  command["fan_stop"] 		= 0x30
  command["fan_silence"] 	= 0x31
  command["fan_low"] 		= 0x32
  command["fan_medium"] 	= 0x33
  command["fan_high"] 		= 0x34
  command["fan_full"] 		= 0x35

  command["powerled_off"]	= 0x4b
  command["powerled_blink"]	= 0x4c
  command["powerled_on"]	= 0x4d
  
  command["beep_short"]		= 0x50
  command["beep_long"]		= 0x51
  
  command["status_red2hz"] 	= 0x54
  command["status_green2hz"] 	= 0x55
  command["status_greenon"] 	= 0x56
  command["status_redon"] 	= 0x57
  command["status_greered2hz"] 	= 0x58
  command["status_off"] 	= 0x59
  command["status_green1hz"] 	= 0x5a
  command["status_red1hz"]	= 0x5b
  command["status_greenred1hz"]	= 0x5c

  command["usb_on"] 		= 0x60 
  command["usb_8hz"] 		= 0x61
  command["usb_off"] 		= 0x62

  serial_port = "/dev/ttyS1"

  def __init__(self):
    """
    this sets up the com interface
    """
    self.fd = serial.Serial(self.serial_port, 19200, timeout=1)
    
  
  def read_serial_events(self):
    """
    grabs a serial event from the local tty
    
    this is a long-running process.  It can be used as the
    main program if all you want to do is monitor the system 
    fans.
    
    """
    
    while 1:
      reader, writer, errors = select.select([self.fd], [], [])
      for r in reader:
        res = r.read(1)
        # print "[%s] %s" % (time.time(), hex(ord(res[0])))
        self.process_data(res)
        
  def set_serial_events(self, event):
    reader, writer, errors = select.select([],[self.fd],[])
    for w in writer:
      res = w.write(event)
    return res

  def send_command(self, status):
    """
    pushes a byte out to the serial console.
    """
    print "Setting status to", status
    res = self.set_serial_events(chr(self.command[status]))
    return res
    


class Ts409(Nas):    
  # status led defs
  model_name 		= "QNAP TS-409"
  temps = {}
  temps['very_low'] 	= range(0,25)
  temps['low'] 		= range(25,43)
  temps['med'] 		= range(43,48)
  temps['high'] 	= range(48,55)
  temps['very_high'] 	= range(55,65)
  temps['critical']	= range(65,100)
  
  def handle_temp(self, temp):
    """
    this should lower and raise the fan, i guess.
    
    The fans have 6 settings:

      fan_stop
      fan_silence
      fan_low
      fan_med
      fan_high
      fan_full
    
    Ideally, the operating range would be covered evenly.  Now,
    how to find out what the temperature ranges should be... :-/
    """
    
    temp = int(temp)
    
    if temp in self.temps['very_low']:
      print "Temp: %s [very_low] => fan off" % temp
      self.send_command("fan_stop")

    if temp in self.temps['low']:
      print "Temp: %s [low] => fan silence" % temp
      self.send_command("fan_silence")

    elif temp in self.temps['med']:
      print "Temp: %s [med] => fan low"  % temp
      self.send_command("fan_low")

    elif temp in self.temps["high"]:
      print "Temp: %s [high] => fan medium!"  % temp
      self.send_command("fan_medium")

    elif temp in self.temps["very_high"]:
      print "Temp: %s [very_high] => fan high!"  % temp
      self.send_command("fan_high")

    elif temp in self.temps["critical"]:
      print "Temp: %s [critical] => fan full! hot stuff! danger!"  % temp
      self.send_command("fan_full")

    else:
      print "Temp: %s [unknown] => danger?"  % temp
      self.send_command("fan_full")
      
  def process_data(self, res):
    """
    figures out what the data from the serial port could mean.
    """
    
    temp_upper = 0xc6
    temp_lower = 0x80
    
    temp_range = range(0x80,0xc7)  
    
    res = ord(res)
    dbg_time = time.time()
    
    if res in temp_range:
      # it's a temperature reading...
      current_temp = int(res) - 128
      print "[%2f] Current temperature: %s" % (dbg_time, current_temp)
      self.handle_temp(current_temp)
    else:
      print "[%2f] Status: %s" % (dbg_time, self.status.get(res, "Unknown"))
      
class Ts212(Ts409):
  """
  this is pretty much the same hardware as a TS-409, AFAICT
  """
  model_name = "QNAP TS-212"

def main():
  nas = Ts212()
  try:
    # nas.send_command("status_off")
    # nas.send_command("usb_8hz")
    # nas.send_command("powerled_off")
    # nas.send_command("beep_short")
    nas.send_command("fan_silence")
    nas.read_serial_events()      
  except KeyboardInterrupt, e:
    print "Brokes!"
    nas.send_command("status_greenon")
    nas.send_command("usb_off")
    nas.send_command("fan_silence")
    nas.send_command("powerled_on")
    
	
  


if __name__=='__main__':
  main()
  