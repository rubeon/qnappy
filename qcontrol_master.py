#!/usr/bin/python
#############################
#
# Envisioned as a grand unified manager for the qnap series of 
# low-end NAS devices.
#
# Use at your own risk.
#
# (c) 2011 Eric Williams <eric@subcritical.org>
#
#
##############################

import evdev
import qcontrol
import select
import glob

from time import sleep

EVDEV_DEVICES=["/dev/input/event0"] #,"/dev/input/event1"]

EVDEV_DEVICES=glob.glob("/dev/input/event*")
"""
    dev = DeviceGroup(sys.argv[1:])
    while 1:
        event = dev.next_event()
        print event
        if event is not None:
            print repr(event)
            if event.type == "EV_KEY" and event.value == 1:
                if event.code.startswith("KEY"):
                    print event.scanCode
                elif event.code.startswith("BTN"):
                    print event.code
                    
                    
from get_next_event...

        r, w, x = select.select(self.fds, [], [], 1)
        for fd in self.fds:
            if fd in r:
                buffer = os.read(fd, self.packetSize)
                event = Event(unpack=buffer)
                return event

        return None
                    
            
"""

def main():
  """
  this monitors the NAS's vitals, and also
  watches for button events.
  """
  nas = qcontrol.Ts212()
  ev  = evdev.DeviceGroup(EVDEV_DEVICES)
  readers = [nas.fd] + ev.fds
  writers = [nas.fd]
  writers = []
  exceptions = []
  
  while 1:
    r, w, x = select.select(readers, writers, exceptions)
    
    for reader in r:
      if reader==nas.fd:
        # print "OMG NASFD"
        nas.process_data(reader.read(1))
    
      elif reader in ev.fds:
        # print "OMG EV!"
        print ev.next_event()

      else:
        pass 
     
  
  
  

if __name__=='__main__':
  main()
  
  