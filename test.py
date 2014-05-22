#Settings 
days_between = .0003
time_to_start = '23:36:00'
times = [5,4,4] 
on = True
zones = [7,11,13]
location = "84123"

rain = 0.00
day = 20
seconds_between = days_between * day
FMT = '%H:%M:%S'

#Set up timer class
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

# Get weather
import urllib2
import json

def check_weather():
    f = urllib2.urlopen('http://api.wunderground.com/api/c5e9d80d2269cb64/geolookup/conditions/q/%s.json' %(location))
    json_string = f.read()
    parsed_json = json.loads(json_string)
    global rain
    rain = parsed_json['current_observation']['precip_today_in']
    f.close()

#Set up GPIO
from datetime import datetime
import threading, time
from time import sleep
import RPi.GPIO as GPIO

GPIO.setup(7, GPIO.OUT)
GPIO.setup(11, GPIO.OUT)
GPIO.setup(13, GPIO.OUT)
GPIO.output(7,False)
GPIO.output(11,False)
GPIO.output(13,False)

now = datetime.now().strftime(FMT)
print (now)

run_at = datetime.strptime(time_to_start, FMT) - datetime.strptime(now, FMT) 
print (run_at)

delay = run_at.total_seconds()
print (delay)

def hello():
    global rt
    rt.stop()
    check_weather()
    print(rain)
    if float(rain) > 0.125:
        print ('Canceling for rain')
        rt = RepeatedTimer(day, hello2)
    else:
        for i in range(0,len(times)):
            print (str(datetime.now()) + ' - Zone ' + str(i+1) + ' on.')
            GPIO.output(zones[i],True)
            print(times[i])
            time.sleep(times[i])
            print ('Zone ' + str(i+1) + ' off.')
            GPIO.output(zones[i],False)
            time.sleep(1)
        print ("Starting Daily...")
        rt = RepeatedTimer(seconds_between, hello2) 

def hello2():
    global rt
    rt.stop()
    check_weather()
    if float(rain) > 0.25:
        print ('Canceling for rain')
        rt = RepeatedTimer(day, hello2)
    else:
        for i in range(0,len(times)):
            print (str(datetime.now()) + ' - Zone ' + str(i+1) + ' on: ' + str(times[i]) + " min.")
            GPIO.output(zones[i],True)
            time.sleep(times[i])
            print ('Zone ' + str(i+1) + ' off.')
            GPIO.output(zones[i],False)
            time.sleep(1)
        rt = RepeatedTimer(seconds_between, hello2)
        
print ("Starting First Time...")
global rt
rt = RepeatedTimer(delay, hello) # it auto-starts, no need of rt.start()

    
try:
    sleep(500) # your long-running job goes here...
finally:
    print("Quitting...")
    rt2.stop() # better in a try/finally block to make sure the program ends!        
    GPIO.setup(7, GPIO.IN)
    GPIO.setup(11, GPIO.IN)
    GPIO.setup(13, GPIO.IN)
