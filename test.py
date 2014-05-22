#Settings 
days_between = .0003
time_to_start = '00:26:00'
times = [5,4,4] 
on = True
zones = [7,11,13]

seconds_between = days_between * 86400
FMT = '%H:%M:%S'

from threading import Timer

class RepeatedTimer(object):
    def __init__(self, interval, function, *args, **kwargs):
        self._timer     = None
        self.function   = function
        self.interval   = interval
        self.args       = args
        self.kwargs     = kwargs
        self.is_running = False
        self.start()

    def _run(self):
        self.is_running = False
        self.start()
        self.function(*self.args, **self.kwargs)

    def start(self):
        if not self.is_running:
            self._timer = Timer(self.interval, self._run)
            self._timer.start()
            self.is_running = True

    def stop(self):
        self._timer.cancel()
        self.is_running = False

from datetime import datetime
import threading, time
from time import sleep
import RPi.GPIO as GPIO

GPIO.setup(7, GPIO.OUT)
GPIO.setup(11, GPIO.OUT)
GPIO.setup(13, GPIO.OUT)

now = datetime.now().strftime(FMT)
print (now)

run_at = datetime.strptime(time_to_start, FMT) - datetime.strptime(now, FMT) 
print (run_at)

delay = run_at.total_seconds()
print (delay)

def hello():
    rt.stop()
    for i in range(0,len(times)):
            print (str(datetime.now()) + ' - Zone ' + str(i+1) + ' on.')
            GPIO.output(zones[i],True)
            print(times[i])
            time.sleep(times[i])
            print ('Zone ' + str(i+1) + ' off.')
            GPIO.output(zones[i],False)
            time.sleep(1)
    print ("Starting Daily...")
    rt2 = RepeatedTimer(seconds_between, hello2) 

def hello2():
    for i in range(0,len(times)):
            print (str(datetime.now()) + ' - Zone ' + str(i+1) + ' on.')
            GPIO.output(zones[i],True)
            print(times[i])
            time.sleep(times[i])
            print ('Zone ' + str(i+1) + ' off.')
            GPIO.output(zones[i],False)
            time.sleep(1)
            
print ("Starting First Time...")
rt = RepeatedTimer(delay, hello) # it auto-starts, no need of rt.start()
try:
    sleep(500) # your long-running job goes here...
finally:
    rt.stop() # better in a try/finally block to make sure the program ends!        
