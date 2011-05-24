#!/usr/bin/python
"""
This is free and unencumbered software released into the public domain.

Anyone is free to copy, modify, publish, use, compile, sell, or
distribute this software, either in source code form or as a compiled
binary, for any purpose, commercial or non-commercial, and by any
means.

In jurisdictions that recognize copyright laws, the author or authors
of this software dedicate any and all copyright interest in the
software to the public domain. We make this dedication for the benefit
of the public at large and to the detriment of our heirs and
successors. We intend this dedication to be an overt act of
relinquishment in perpetuity of all present and future rights to this
software under copyright law.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.

For more information, please refer to <http://unlicense.org/>

"""

import socket
import select
import io
import time
import serial
import logging

module_logger = logging.getLogger("qnappy.qcontrol")

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
  model_name = "Generic QNAP NAS"
  command = {}
  temps = {}
  temps['very_low'] 	= range(0,25)
  temps['low'] 		= range(25,45)
  temps['med'] 		= range(45,48)
  temps['high'] 	= range(48,55)
  temps['very_high'] 	= range(55,65)
  temps['critical']	= range(65,100)
  current_temp = 0

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
    self.logger = logging.getLogger("qnappy.qcontrol.%s" % self.model_name)
    self.last_fanspeed_change = 0 	# not using time.time(), so we can make sure to get a proper
                                        # initial fanspeed for our current temperature....
    self.fanspeed = ""

    
  
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
    self.logger.info("Setting status to %s" % status)
    res = self.set_serial_events(chr(self.command[status]))
    return res
    
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
    
    There's a 120 second lead time on fan speed changes, to avoid 
    flapping. Listening to fan-speed changes every 5 seconds is
    annoying.
    
    """
    
    temp = int(temp)
    self.logger.debug("Time since last speed change: %.2f [%dC][%s]" % (time.time() - self.last_fanspeed_change, temp, self.fanspeed))
    if temp != self.current_temp and (time.time() - self.last_fanspeed_change > 300):
      # we've had a temperature change
      if temp in self.temps['very_low']:
        self.logger.info("Temp: %s [very_low] => fan off" % temp)
        self.fanspeed = "fan_stop"
        self.send_command("fan_stop")

      if temp in self.temps['low']:
        self.logger.info("Temp: %s [low] => fan silence" % temp)
        self.fanspeed = "fan_silence"
        self.send_command("fan_silence")

      elif temp in self.temps['med']:
        self.logger.info("Temp: %s [med] => fan low"  % temp)
        self.fanspeed = "fan_low"
        self.send_command("fan_low")

      elif temp in self.temps["high"]:
        self.logger.info("Temp: %s [high] => fan medium!"  % temp)
        self.fanspeed = "fan_medium"
        self.send_command("fan_medium")

      elif temp in self.temps["very_high"]:
        self.logger.info("Temp: %s [very_high] => fan high!"  % temp)
        self.fanspeed = "fan_high"
        self.send_command("fan_high")

      elif temp in self.temps["critical"]:
        self.logger.info("Temp: %s [critical] => fan full! hot stuff! danger!"  % temp)
        self.fanspeed = "fan_full"
        self.send_command("fan_full")

      else:
        self.logger.info("Temp: %s [unknown] => danger?"  % temp )
        self.fanspeed = "fan_full"
        self.send_command("fan_full")
      self.last_fanspeed_change = time.time()

    self.current_temp = temp

      
  def process_data(self, res):
    """
    figures out what the data from the serial port could mean. Takes 1 byte
    of input from the serial port.
    """
    temp_range = range(0x80,0xc7)  
    
    res = ord(res)
    # dbg_time = time.time()
    
    if res in temp_range:
      # it's a temperature reading...
      current_temp = int(res) - 128
      self.logger.debug("Current temperature: %s" % (current_temp) )
      self.handle_temp(current_temp)
    else:
      self.logger.debug("Status: %s" % self.status.get(res, "Unknown"))



class Ts409(Nas):    
  # status led defs
  model_name 		= "QNAP TS-409"
    
      
class Ts219(Ts409):
  """
  this is pretty much the same hardware as a TS-409, AFAICT
  """
  model_name = "QNAP TS-219"

def main():
  nas = Ts219()
  try:
    # nas.send_command("status_off")
    # nas.send_command("usb_8hz")
    # nas.send_command("powerled_off")
    # nas.send_command("beep_short")
    nas.send_command("fan_silence")
    nas.read_serial_events()      
  except KeyboardInterrupt, e:
    self.logger.info("Brokes!")
    nas.send_command("status_greenon")
    nas.send_command("usb_off")
    nas.send_command("fan_silence")
    nas.send_command("powerled_on")
    
	
  


if __name__=='__main__':
  main()
  