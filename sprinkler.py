#Settings 
days_between = .0001
<<<<<<< HEAD
time_to_start = '00:35:00'
=======
time_to_start = '15:35:00'
>>>>>>> 69c32ef48ca741f14fe998768f889d2ffc58d4a3
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
<<<<<<< HEAD
        for i in range(0,3):
            print ('Zone ' + str(i+1) + ' on.')
=======
        for i in range(0,len(times)):
            print (str(datetime.now()) + ' - Zone ' + str(i+1) + ' on.')
>>>>>>> 69c32ef48ca741f14fe998768f889d2ffc58d4a3
            GPIO.output(zones[i],True)
            print(times[i])
            time.sleep(times[i])
            print ('Zone ' + str(i+1) + ' off.')
            GPIO.output(zones[i],False)
            time.sleep(30)
        threading.Timer(seconds_between, go).start()

threading.Timer(delay, go).start()
