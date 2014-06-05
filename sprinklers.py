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
   'time_to_start' : '14:59:00',
   'message' : '',
   'system_running' : False,
   'log' : {},
   'next_run_date':''
   }

#Setup
day = 86400
seconds_between = 0.0
def get_seconds():
    global seconds_between
    seconds_between = templateData['days'] * day
    #print (seconds_between)
get_seconds()    
#FMT = '%H:%M:%S'
cycle_running = 0
total_sprink_time = 0
cycle_has_run = False

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
        templateData['rain'] = weather_test

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

def get_start_time():
    now = datetime.now()
    print(now)

    splits = templateData['time_to_start'].split(":")
    time_to_start = datetime.now().replace(hour=int(splits[0]), minute=int(splits[1]), second=00, microsecond=0)

    run_at = time_to_start - now
    if run_at.total_seconds() < 0:
        print(time_to_start.replace(day=time_to_start.day+1))
        run_at = (time_to_start.replace(day=time_to_start.day+1)) - now

    global delay
    delay = run_at.total_seconds()
    sec = timedelta(seconds=delay)
    d = datetime(1,1,1) + sec
    print("Starting in %d hours and %d minutes" %(d.hour, d.minute))
    return delay

def write_log(message):
    import os
    if os.path.getsize('log.log') > 1000000:
        f = open('log.log','w')
        f.write(message)
        f.close()
    else:
        f = open('log.log','a')
        f.write(message)
        f.close()

# Run program
def hello():
    global rt
    rt.stop()
    check_weather()
    print(str(templateData['rain']) + " inches of rain")
    global total_sprink_time
    if float(templateData['rain']) > 0.125:
        write_log('%s - Canceling for rain - trying again in 24 hours.\n' %(datetime.now().strftime('%m/%d/%Y %I:%M %p')))
        rt = RepeatedTimer(day, hello)
    else:
        global cycle_running
        global cycle_has_run
        cycle_running = 1
        templateData['message'] = 'Running Cycle'
        
        total_sprink_time = 0
        for zone in zones:
            write_log('%s - %s on: %s min.\n' %(datetime.now().strftime('%m/%d/%Y %I:%M %p'),zones[zone]['name'],zones[zone]['length']))
            if on_pi:
                GPIO.output(zones[zone]['pinNo'],True)
            zones[zone]['on'] = True
            time.sleep(int(zones[zone]['length'])*60)
            total_sprink_time += int(zones[zone]['length'])*60

            write_log('%s - %s off.\n' %(datetime.now().strftime('%m/%d/%Y %I:%M %p'),zones[zone]['name']))
            if on_pi:
                GPIO.output(zones[zone]['pinNo'],False)
            zones[zone]['on'] = False
            time.sleep(5)
            total_sprink_time += 5
        
        rt = RepeatedTimer(int(seconds_between)-total_sprink_time, hello)
        global next_time
        next_time = datetime.now() + timedelta(seconds=int(seconds_between)-total_sprink_time)
        templateData['next_run_date'] = next_time.strftime('%a, %B %d at %I:%M %p')
        cycle_running = 0
        cycle_has_run = True
        templateData['message'] = ''
        
        

# Web part
try:
    
    @app.route('/')
    def my_form():
        templateData['log'] = [log.rstrip('\n') for log in open('log.log')]
        return render_template("index2.html", **templateData)

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
            global rt
            global cycle_has_run
            if cycle_has_run:
                if templateData['system_running']:
                    rt.stop()
                    templateData['time_to_start'] = str(ttime)
                    splits = templateData['time_to_start'].split(":")
                    temp = next_time.replace(hour=int(splits[0]), minute=int(splits[1]), second=00, microsecond=0) - datetime.now()
                    templateData['next_run_date'] = next_time.replace(hour=int(splits[0]), minute=int(splits[1]), second=00, microsecond=0).strftime('%a, %B %d at %I:%M %p')
                    check_weather()
                    rt = RepeatedTimer(temp.total_seconds(), hello)
                else:
                    templateData['time_to_start'] = str(ttime)
            else:
                if templateData['system_running']:
                    rt.stop()
                    templateData['time_to_start'] = str(ttime)
                    get_start_time()
                    temp = datetime.now() + timedelta(seconds=delay)
                    templateData['next_run_date'] = temp.strftime('%a, %B %d at %I:%M %p')
                    check_weather()
                    rt = RepeatedTimer(delay, hello)
                else:
                    templateData['time_to_start'] = str(ttime)
        if zone1 != '':
            zones['zone1']['length'] = int(zone1)
        if zone2 != '':
            zones['zone2']['length'] = int(zone2)
        if zone3 != '':
            zones['zone3']['length'] = int(zone3)
        templateData['message'] = 'Updated Settings'    
        return render_template("index2.html", **templateData)

    @app.route("/<changePin>/<action>")
    def action(changePin, action):
        if templateData['system_running']:
            if cycle_running == 0:
                global system_running
                if action == "on":
                    if zones['zone1']['on'] or zones['zone2']['on'] or zones['zone3']['on']:
                        templateData['messages'] = "Program Running"
                    else:    
                        zones[changePin]['on'] = True
                        system_running = 1
                        if on_pi:
                            GPIO.output(zones[changePin]['pinNo'],True)
                        else:
                            print (changePin + " on.")
                        templateData['message'] = "Turned " + zones[changePin]['name'] + " on."
                        write_log('%s - Manually turned %s on.\n' %(datetime.now().strftime('%m/%d/%Y %I:%M %p'),zones[changePin]['name']))
                if action == "off":
                    zones[changePin]['on'] = False
                    system_running = 0
                    if on_pi:
                        GPIO.output(zones[changePin]['pinNo'],False)
                    else:
                        print (changePin + " off.")    
                    templateData['message'] = "Turned " + zones[changePin]['name'] + " off."
                    write_log('%s - Manually turned %s off.\n' %(datetime.now().strftime('%m/%d/%Y %I:%M %p'),zones[changePin]['name']))
            else:
                templateData['message'] = 'Cycle Running'
        else:
            templateData['message'] = 'System Not On'
        return redirect(url_for('my_form'))
        
    @app.route("/start")
    def start_program():
        if templateData['system_running'] == False:
            get_start_time()
            temp = datetime.now() + timedelta(seconds=delay)
            templateData['next_run_date'] = temp.strftime('%a, %B %d at %I:%M %p')
            check_weather()
            global rt
            rt = RepeatedTimer(delay, hello)
            templateData['system_running'] = True
            templateData['message'] = "System Started"
            write_log('%s - System started.\n' %(datetime.now().strftime('%m/%d/%Y %I:%M %p')))
        return redirect(url_for('my_form'))

    @app.route("/stop")
    def stop_program():
        if templateData['system_running'] == True:
            global rt
            rt.stop()
            templateData['system_running'] = False
            templateData['message'] = "System Stopped"
            write_log('%s - System stopped.\n' %(datetime.now().strftime('%m/%d/%Y %I:%M %p')))
        return redirect(url_for('my_form'))
    
    if __name__ == '__main__':
        app.run(host='0.0.0.0')
    
finally:
    print("Quitting...")
    global rt
    rt.stop() # better in a try/finally block to make sure the program ends!        
    if on_pi:
        GPIO.setup(7, GPIO.IN)
        GPIO.setup(11, GPIO.IN)
        GPIO.setup(13, GPIO.IN)
