#Settings 
on = True
location = "84123"
on_pi=False
weather_test = 0
zones = {
    'zone1' : {'length':40,'on':False,'pinNo':7, 'name':'Zone 1'},
    'zone2' : {'length':30,'on':False,'pinNo':11, 'name':'Zone 2'},
    'zone3' : {'length':30,'on':False,'pinNo':13, 'name':'Zone 3'},
    }
templateData = {
   'days' : 3,
   'zones' : zones,
   'rain' : 0.0,
   'time_to_start' : '20:19:00',
   'message' : ''
   }

#Setup
day = 86400
seconds_between = 0.0
def get_seconds():
    global seconds_between
    seconds_between = templateData['days'] * day
    print (seconds_between)
get_seconds()    
FMT = '%H:%M:%S'
system_running = 0
program_running = 0
total_sprink_time = 0

#Set up Flask
from flask import Flask, request, render_template, url_for, flash, redirect
import time
from threading import Thread

app = Flask(__name__)

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
if on_pi:
    import urllib2
else:
    from urllib.request import urlopen 
import json

def check_weather():
    if weather_test == 100:
        if on_pi:
            f = urllib2.urlopen('http://api.wunderground.com/api/c5e9d80d2269cb64/geolookup/conditions/q/%s.json' %(location))
        else:
            f = urlopen('http://api.wunderground.com/api/c5e9d80d2269cb64/geolookup/conditions/q/%s.json' %(location))
        json_string = f.read()
        parsed_json = json.loads(json_string.decode("utf8"))
        templateData['rain'] = parsed_json['current_observation']['precip_today_in']
        f.close()
    else:
        templateData['rain'] = str(weather_test)

#Set up GPIO
from datetime import datetime, timedelta
import threading, time
from time import sleep
if on_pi:
    import RPi.GPIO as GPIO

    GPIO.setup(7, GPIO.OUT)
    GPIO.setup(11, GPIO.OUT)
    GPIO.setup(13, GPIO.OUT)
    GPIO.output(7,False)
    GPIO.output(11,False)
    GPIO.output(13,False)

now = datetime.now()
print (now)

splits = templateData['time_to_start'].split(":")
time_to_start = datetime.now().replace(hour=int(splits[0]), minute=int(splits[1]), second=00, microsecond=0)

run_at = time_to_start - now
if run_at.total_seconds() < 0:
    print (time_to_start.replace(day=time_to_start.day+1))
    run_at = (time_to_start.replace(day=time_to_start.day+1)) - now

delay = run_at.total_seconds()
sec = timedelta(seconds=delay)
d = datetime(1,1,1) + sec
print ("Starting in %d hours and %d minutes" %(d.hour, d.minute))

# Run program
def hello():
    global rt
    rt.stop()
    check_weather()
    print(templateData['rain'] + " inches of rain")
    global total_sprink_time
    if float(templateData['rain']) > 0.125:
        print ('Canceling for rain')
        rt = RepeatedTimer(day, hello)
    else:
        global program_running
        program_running = 1
        templateData['message'] = 'Running Program'
        
        total_sprink_time = 0
        for zone in zones:
            print ('%s - %s on: %s min.' %(str(datetime.now()),zones[zone]['name'],zones[zone]['length']))
            if on_pi:
                GPIO.output(zones[zone]['pinNo'],True)
            zones[zone]['on'] = True
            time.sleep(int(zones[zone]['length'])*60)
            total_sprink_time += int(zones[zone]['length'])*60

            print ('%s - %s off.' %(str(datetime.now()),zones[zone]['name']))
            if on_pi:
                GPIO.output(zones[zone]['pinNo'],False)
            zones[zone]['on'] = False
            time.sleep(5)
            total_sprink_time += 5
        
        rt = RepeatedTimer(int(seconds_between)-total_sprink_time, hello)    
        program_running = 0
        templateData['message'] = ''
        
        

print ("Starting First Time...")
global rt
rt = RepeatedTimer(delay, hello) # it auto-starts, no need of rt.start()
    
# Web part
try:
    
    @app.route('/')
    def my_form():
        return render_template("index.html", **templateData)

    @app.route('/', methods=['POST'])
    def my_form_post():
        text = request.form['text']
        ttime = request.form['start']
        zone1 = request.form['zone1']
        zone2 = request.form['zone2']
        zone3 = request.form['zone3']
        if text != '':
            templateData['days'] = float(text)
            get_seconds()
        if ttime != '':
            templateData['time_to_start'] = str(ttime)
        if zone1 != '':
            zones['zone1']['length'] = int(zone1)
        if zone2 != '':
            zones['zone2']['length'] = int(zone2)
        if zone3 != '':
            zones['zone3']['length'] = int(zone3)
        templateData['message'] = 'Updated Settings'    
        return render_template("index.html", **templateData)

    @app.route("/<changePin>/<action>")
    def action(changePin, action):
        if program_running == 0:
            global system_running
            if action == "on" and system_running == 0:
                zones[changePin]['on'] = True
                system_running = 1
                if on_pi:
                    GPIO.output(zones[changePin]['pinNo'],True)
                else:
                    print (changePin + " on.")
                templateData['message'] = "Turned " + zones[changePin]['name'] + " on."
            if action == "off":
                zones[changePin]['on'] = False
                system_running = 0
                if on_pi:
                    GPIO.output(zones[changePin]['pinNo'],False)
                else:
                    print (changePin + " off.")    
                templateData['message'] = "Turned " + zones[changePin]['name'] + " off."
        return redirect(url_for('my_form'))
        
            
            
    if __name__ == '__main__':
        app.run(host='0.0.0.0')
    
finally:
    print("Quitting...")
    rt.stop() # better in a try/finally block to make sure the program ends!        
    if on_pi:
        GPIO.setup(7, GPIO.IN)
        GPIO.setup(11, GPIO.IN)
        GPIO.setup(13, GPIO.IN)
