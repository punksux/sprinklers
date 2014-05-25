#Settings 
days_between = .0001
time_to_start = '15:59:00'
#zone1_time = 40 
#zone2_time = 30 
#zone3_time = 30 
times = [40,30,30] 
on = True
zones = [7,11,13]

#App
FMT = '%H:%M:%S'
seconds_between = days_between * 86400

from datetime import datetime
import threading, time
import RPi.GPIO as GPIO

GPIO.setup(7, GPIO.OUT)
GPIO.setup(11, GPIO.OUT)
GPIO.setup(13, GPIO.OUT)
GPIO.output(7,True)
GPIO.output(11,True)
GPIO.output(13,True)

now = datetime.now().strftime(FMT)
print (now)

run_at = datetime.strptime(time_to_start, FMT) - datetime.strptime(now, FMT) 
print (run_at)

delay = run_at.total_seconds()
print (delay)

def turn_off():
    on = False

def go():
    if (on):
        for i in range(0,len(times)):
            print (str(datetime.now()) + ' - Zone ' + str(i+1) + ' on.')
            GPIO.output(zones[i],False)
            print(times[i])
            time.sleep(times[i])
            print ('Zone ' + str(i+1) + ' off.')
            GPIO.output(zones[i],True)
            time.sleep(4)
        threading.Timer(seconds_between, go).start()

threading.Timer(delay, go).start()
