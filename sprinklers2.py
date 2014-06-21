with open('settings.ini') as f:
    content = f.readlines()
# Settings
on = True
location = "84123"
on_pi = False
weather_test = 100
zones = [
    {'length': int(content[2].rstrip('\r\n')), 'on': False, 'pinNo': 7, 'name': 'Zone 1'},
    {'length': int(content[3].rstrip('\r\n')), 'on': False, 'pinNo': 11, 'name': 'Zone 2'},
    {'length': int(content[4].rstrip('\r\n')), 'on': False, 'pinNo': 13, 'name': 'Zone 3'},
]
templateData = {
    'days': float(content[0].rstrip('\r\n')),
    'zones': zones,
    'rain': 0.0,
    'time_to_start': str(content[1].rstrip('\r\n')),
    'message': '',
    'system_running': False,
    'log': {},
    'next_run_date': ''
}

# Setup
job = None
cycle_running = 0
cycle_has_run = False

# Imports
from flask import Flask, request, render_template, url_for, redirect
from datetime import datetime, timedelta
import time
import os
import platform
from apscheduler.scheduler import Scheduler

sched = Scheduler()
sched.start()

if platform.uname()[0] != 'Windows':
    print(platform.uname()[0])
    on_pi = True
else:
    print(platform.uname()[0])

if on_pi:
    import urllib2
    import RPi.GPIO as GPIO
else:
    from urllib.request import urlopen
import json

#Set up Flask
app = Flask(__name__)

# Get weather
time_checked = datetime.now()
time_checked = time_checked.replace(day=1)

def check_weather():
    global time_checked
    temp = datetime.now() - time_checked
    if weather_test == 100:
        if temp.total_seconds() > (60 * 60):
            weather_website = ('http://api.wunderground.com/api/c5e9d80d2269cb64/conditions/q/%s.json' % location)
            if on_pi:
                f = urllib2.urlopen(weather_website)
            else:
                f = urlopen(weather_website)
            json_string = f.read()
            parsed_json = json.loads(json_string.decode("utf8"))
            templateData['rain'] = parsed_json['current_observation']['precip_today_in']
            f.close()
            time_checked = datetime.now()
    else:
        templateData['rain'] = weather_test

#Set up GPIO
if on_pi:
    GPIO.setup(7, GPIO.OUT)
    GPIO.setup(11, GPIO.OUT)
    GPIO.setup(13, GPIO.OUT)
    GPIO.output(7, True)
    GPIO.output(11, True)
    GPIO.output(13, True)


def get_start_time():
    splits = templateData['time_to_start'].split(":")
    ini_time = datetime.strptime(content[5].rstrip('\r\n'), '%Y-%m-%d %H:%M:%S')
    global time_to_start
    time_to_start = ini_time.replace(hour=int(splits[0]), minute=int(splits[1]), second=00, microsecond=0)
    print (time_to_start)
    if (time_to_start - datetime.now()).total_seconds() < 0:
        time_to_start = time_to_start + timedelta(days=1)
    write_settings(5, time_to_start)
    return time_to_start


nday = datetime.now()
nday = nday.day

def write_log(message):
    tday = datetime.now()
    tday = tday.day
    global nday
    if tday != nday:
        f = open('log.log', 'a')
        f.write('-=\n')
        f.close()
    if os.path.getsize('log.log') > 1000000:
        f = open('log.log', 'w')
        f.write(message)
        f.close()
        nday = tday
    else:
        f = open('log.log', 'a')
        f.write(message)
        f.close()
        nday = tday


def write_settings(line, value):
    lines = open('settings.ini', 'r').readlines()
    lines[line] = str(value) + '\n'
    out = open('settings.ini', 'w')
    out.writelines(lines)
    out.close()

def isTimeFormat(input):
    try:
        time.strptime(input, '%H:%M')
        return True
    except ValueError:
        return False

# Run program
def hello():
    check_weather()
    print(datetime.now())
    global job
    if float(templateData['rain']) > 0.125:
        write_log(
            '%s - Canceling for rain - trying again in 24 hours.\n' % (datetime.now().strftime('%m/%d/%Y %I:%M %p')))
        temp = datetime.now() + timedelta(days=1)
        job = sched.add_date_job(hello, temp)
    else:
        global cycle_running
        global cycle_has_run
        global next_time
        cycle_running = 1
        templateData['message'] = 'Running Cycle'
        next_time = datetime.now() + timedelta(days=templateData['days'])

        for i in range(0, len(zones)):
            write_log('%s - %s on: %s min.\n' % (
                datetime.now().strftime('%m/%d/%Y %I:%M %p'), zones[i]['name'], zones[i]['length']))
            if on_pi:
                GPIO.output(zones[i]['pinNo'], False)
            else:
                print('%s - %s on: %s min.\n' % (
                datetime.now().strftime('%m/%d/%Y %I:%M %p'), zones[i]['name'], zones[i]['length']))
            zones[i]['on'] = True
            time.sleep((int(zones[i]['length'])) * 60)

            write_log('%s - %s off.\n' % (datetime.now().strftime('%m/%d/%Y %I:%M %p'), zones[i]['name']))
            if on_pi:
                if i < len(zones) - 1:
                    GPIO.output(zones[i + 1]['pinNo'], False)
                time.sleep(5)
                GPIO.output(zones[i]['pinNo'], True)
            else:
                print('%s - %s off.\n' % (datetime.now().strftime('%m/%d/%Y %I:%M %p'), zones[i]['name']))
            zones[i]['on'] = False
            time.sleep(5)

        job = sched.add_date_job(hello, next_time)
        write_settings(5, next_time.strftime('%Y-%m-%d %H:%M:%S'))
        print (next_time)
        templateData['next_run_date'] = next_time.strftime('%a, %B %d at %I:%M %p')
        cycle_running = 0
        cycle_has_run = True
        templateData['message'] = ''


# Web part
try:

    @app.route('/')
    def my_form():
        templateData['log'] = [log.rstrip('\n') for log in open('log.log')]
        check_weather()
        return render_template("index.html", **templateData)

    @app.route('/', methods=['POST'])
    def my_form_post():
        text = request.form['text']
        ttime = request.form['start']
        zone1 = request.form['0']
        zone2 = request.form['1']
        zone3 = request.form['2']
        if text != '':
            templateData['days'] = float(text)
            write_settings(0, text)
        if ttime != '':
            if isTimeFormat(ttime):
                global cycle_has_run
                global job
                if cycle_has_run:
                    if templateData['system_running']:
                        sched.unschedule_job(job)
                        templateData['time_to_start'] = str(ttime)
                        write_settings(1, str(ttime))
                        splits = templateData['time_to_start'].split(":")
                        temp = next_time.replace(hour=int(splits[0]), minute=int(splits[1]), second=00,
                                                microsecond=0)
                        templateData['next_run_date'] = temp.strftime('%a, %B %d at %I:%M %p')
                        check_weather()
                        job = sched.add_date_job(hello, temp)
                    else:
                        templateData['time_to_start'] = str(ttime)
                        write_settings(1, str(ttime))
                else:
                    if templateData['system_running']:
                        sched.unschedule_job(job)
                        templateData['time_to_start'] = str(ttime)
                        write_settings(1, str(ttime))
                        get_start_time()
                        templateData['next_run_date'] = time_to_start.strftime('%a, %B %d at %I:%M %p')
                        check_weather()
                        job = sched.add_date_job(hello, time_to_start)
                    else:
                        templateData['time_to_start'] = str(ttime)
                        write_settings(1, str(ttime))
            else:
                templateData['message'] = 'Error: Incorrect Time'
        if zone1 != '':
            zones[0]['length'] = int(zone1)
            write_settings(2, zone1)
        if zone2 != '':
            zones[1]['length'] = int(zone2)
            write_settings(3, zone2)
        if zone3 != '':
            zones[2]['length'] = int(zone3)
            write_settings(4, zone3)
        templateData['message'] = 'Updated Settings'
        return render_template("index.html", **templateData)

    @app.route("/<change_pin>/<action>")
    def action(change_pin, action):
        if templateData['system_running']:
            if cycle_running == 0:
                global system_running
                if action == "on":
                    if zones[0]['on'] or zones[1]['on'] or zones[2]['on']:
                        templateData['messages'] = "Program Running"
                    else:
                        zones[int(change_pin)]['on'] = True
                        system_running = 1
                        if on_pi:
                            GPIO.output(zones[int(change_pin)]['pinNo'], False)
                        else:
                            print(zones[int(change_pin)]['name'] + " on.")
                        templateData['message'] = "Turned " + zones[int(change_pin)]['name'] + " on."
                        write_log('%s - Manually turned %s on.\n' % (
                            datetime.now().strftime('%m/%d/%Y %I:%M %p'), zones[int(change_pin)]['name']))
                if action == "off":
                    zones[int(change_pin)]['on'] = False
                    system_running = 0
                    if on_pi:
                        GPIO.output(zones[int(change_pin)]['pinNo'], True)
                    else:
                        print(zones[int(change_pin)]['name'] + " off.")
                    templateData['message'] = "Turned " + zones[int(change_pin)]['name'] + " off."
                    write_log('%s - Manually turned %s off.\n' % (
                        datetime.now().strftime('%m/%d/%Y %I:%M %p'), zones[int(change_pin)]['name']))
            else:
                templateData['message'] = 'Cycle Running'
        else:
            templateData['message'] = 'System Not On'
        return redirect(url_for('my_form'))

    @app.route("/start")
    def start_program():
        if templateData['system_running'] is False:
            get_start_time()
            templateData['next_run_date'] = time_to_start.strftime('%a, %B %d at %I:%M %p')
            global job
            job = sched.add_date_job(hello, time_to_start)
            templateData['system_running'] = True
            templateData['message'] = "System Started"
            write_log('%s - System started.\n' % (datetime.now().strftime('%m/%d/%Y %I:%M %p')))
        return redirect(url_for('my_form'))

    @app.route("/stop")
    def stop_program():
        if templateData['system_running']:
            sched.unschedule_job(job)
            templateData['system_running'] = False
            templateData['message'] = "System Stopped"
            templateData['next_run_date'] = ''
            write_log('%s - System stopped.\n' % (datetime.now().strftime('%m/%d/%Y %I:%M %p')))
        return redirect(url_for('my_form'))

    if __name__ == '__main__':
        app.run(host='0.0.0.0')

finally:
    print("Quitting...")
    sched.shutdown()
    if on_pi:
        GPIO.setup(7, GPIO.IN)
        GPIO.setup(11, GPIO.IN)
        GPIO.setup(13, GPIO.IN)
