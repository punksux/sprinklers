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
    'rain_total': float(content[6].rstrip('\r\n')),
    'time_to_start': str(content[1].rstrip('\r\n')),
    'message': '',
    'system_running': False,
    'log': {},
    'next_run_date': '',
    'cycle_count': 0,
    'uptime': ''
}

# Imports
from flask import Flask, request, render_template, url_for, redirect
from datetime import datetime, timedelta
import time
import os
import platform
from apscheduler.scheduler import Scheduler
from socket import timeout
import logging
import logging.handlers

# Setup
job = None
cycle_running = 0
cycle_has_run = False
uptime_counter = datetime.now()

# Set up logging
open('errors.log', 'w').close()
logging.basicConfig(filename='errors.log', level=logging.ERROR, format='%(asctime)s - %(levelname)s: %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S %p')

#Set platform
logging.info("** Running on " + platform.uname()[0] + " **")
if platform.uname()[0] != 'Windows':
    on_pi = True

sched = Scheduler()
sched.start()

if on_pi:
    import urllib2
    import RPi.GPIO as GPIO
    import socket
else:
    from urllib.request import urlopen
    import urllib.error
import json

#Set up Flask
app = Flask(__name__)

# Get weather
time_checked = datetime.now().replace(day=1)


def check_weather():
    global time_checked
    temp = datetime.now() - time_checked
    if weather_test == 100:
        if temp.total_seconds() > (10 * 60):
            global something_wrong
            global f
            weather_website = ('http://api.wunderground.com/api/c5e9d80d2269cb64/conditions/q/%s.json' % location)
            if on_pi:
                try:
                    f = urllib2.urlopen(weather_website, timeout=3)
                    something_wrong = False
                except urllib2.URLError as e:
                    logging.error('%s - Data not retrieved because %s' % datetime.now().strftime('%m/%d/%Y %I:%M %p'),
                                  e)
                    something_wrong = True
                except socket.timeout:
                    logging.error('%s - Socket timed out' % datetime.now().strftime('%m/%d/%Y %I:%M %p'))
                    something_wrong = True
            else:
                try:
                    f = urlopen(weather_website, timeout=3)
                    something_wrong = False
                except urllib.error.URLError as e:
                    logging.error('%s - Data not retrieved because %s' % datetime.now().strftime('%m/%d/%Y %I:%M %p'),
                                  e)
                    something_wrong = True
                except timeout:
                    logging.error('%s - Socket timed out' % datetime.now().strftime('%m/%d/%Y %I:%M %p'))
                    something_wrong = True

            if something_wrong:
                logging.error("%s - No Internet" % datetime.now().strftime('%m/%d/%Y %I:%M %p'))
                templateData['rain'] = 0.0
            else:
                json_string = f.read()
                parsed_json = json.loads(json_string.decode("utf8"))
                templateData['rain'] = parsed_json['current_observation']['precip_today_in']
                f.close()
                logging.info("Checking weather - " + str(templateData['rain']) + " inches of rain")
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
    with open('settings.ini') as f:
        content = f.readlines()
    ini_time = datetime.strptime(content[5].rstrip('\r\n'), '%Y-%m-%d %H:%M:%S')
    global time_to_start
    time_to_start = ini_time.replace(hour=int(splits[0]), minute=int(splits[1]), second=00, microsecond=0)
    print(time_to_start)
    if (time_to_start - datetime.now()).total_seconds() < 0:
        time_to_start = datetime.now().replace(hour=int(splits[0]), minute=int(splits[1]), second=00, microsecond=0)
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


def is_time_format(tinput):
    try:
        time.strptime(tinput, '%H:%M')
        return True
    except ValueError:
        return False


def turn_on(zone):
    zones[int(zone)]['on'] = True
    if on_pi:
        GPIO.output(zones[int(zone)]['pinNo'], False)
    else:
        print(zones[int(zone)]['name'] + " on.")


def turn_off(zone):
    zones[int(zone)]['on'] = False
    if on_pi:
        GPIO.output(zones[int(zone)]['pinNo'], True)
    else:
        print(zones[int(zone)]['name'] + " off.")


def rain_total():
    check_weather()
    templateData['rain_total'] += float(templateData['rain'])
    write_settings(6, templateData['rain_total'])

sched.add_interval_job(rain_total, days=1, start_date=datetime.now().replace(hour=23, minute=30, second=00,
                                                                             microsecond=00))


def time_since(otherdate):
    dt = datetime.now() - otherdate
    offset = dt.seconds
    delta_s = offset % 60
    offset /= 60
    delta_m = offset % 60
    offset /= 60
    delta_h = offset % 24
    delta_d = dt.days

    if delta_d >= 1:
        return "%d %s, %d %s, %d %s" % (delta_d, "day" if 2 > delta_d > 1 else "days", delta_h,
                                        "hour" if 2 > delta_h > 1 else "hours", delta_m,
                                        "minute" if 2 > delta_m > 1 else "minutes")
    if delta_h >= 1:
        return "%d %s, %d %s" % (delta_h, "hour" if 2 > delta_h > 1 else "hours",
                                 delta_m, "minute" if 2 > delta_m > 1 else "minutes")
    if delta_m >= 1:
        return "%d %s, %d %s" % (delta_m, "minute" if 2 > delta_m > 1 else "minutes", delta_s,
                                 "second" if 2 > delta_s > 1 else "seconds")
    else:
        return "%d %s" % (delta_s, "second" if 2 > delta_s > 1 else "seconds")


# Run program
def sprinkler_go():
    check_weather()
    templateData['rain_total'] += float(templateData['rain'])
    print(datetime.now())
    global job
    if float(templateData['rain']) > 0.2 or float(templateData['rain_total']) > (int(templateData['days'])*.125):
        write_log('%s - Canceling for rain - trying again in %s days.\n' %
                  (datetime.now().strftime('%m/%d/%Y %I:%M %p'), str(templateData['days'])))
        temp = datetime.now() + timedelta(days=int(templateData['days']))
        job = sched.add_date_job(sprinkler_go, temp)
        templateData['next_run_date'] = temp.strftime('%a, %B %d at %I:%M %p')
        templateData['rain_total'] = 0.0
        write_settings(6, templateData['rain_total'])
    elif float(templateData['rain']) > 0.1 or float(templateData['rain_total']) > (int(templateData['days'])*.063):
        write_log('%s - Canceling for rain - trying again tomorrow.\n' % (datetime.now().strftime('%m/%d/%Y %I:%M %p')))
        temp = datetime.now() + timedelta(days=1)
        job = sched.add_date_job(sprinkler_go, temp)
        templateData['next_run_date'] = temp.strftime('%a, %B %d at %I:%M %p')
        templateData['rain_total'] = 0.0
        write_settings(6, templateData['rain_total'])
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

        job = sched.add_date_job(sprinkler_go, next_time)
        write_settings(5, next_time.strftime('%Y-%m-%d %H:%M:%S'))
        print(next_time)
        templateData['next_run_date'] = next_time.strftime('%a, %B %d at %I:%M %p')
        cycle_running = 0
        templateData['cycle_count'] += 1
        cycle_has_run = True
        templateData['rain_total'] = 0.0
        write_settings(6, templateData['rain_total'])
        templateData['message'] = ''


# Web part
try:

    @app.route('/')
    def my_form():
        templateData['log'] = [log.rstrip('\n') for log in open('log.log')]
        check_weather()
        templateData['uptime'] = time_since(uptime_counter)
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
            if is_time_format(ttime):
                global cycle_has_run
                global job
                if cycle_has_run:
                    if templateData['system_running']:
                        sched.unschedule_job(job)
                        templateData['time_to_start'] = str(ttime)
                        write_settings(1, str(ttime))
                        splits = templateData['time_to_start'].split(":")
                        temp = next_time.replace(hour=int(splits[0]), minute=int(splits[1]), second=00, microsecond=0)
                        templateData['next_run_date'] = temp.strftime('%a, %B %d at %I:%M %p')
                        check_weather()
                        job = sched.add_date_job(sprinkler_go, temp)
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
                        job = sched.add_date_job(sprinkler_go, time_to_start)
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
        templateData['uptime'] = time_since(uptime_counter)
        return render_template("index.html", **templateData)

    @app.route("/<change_pin>/<action>/<length>")
    def action(change_pin, action, length):
        if templateData['system_running']:
            if cycle_running == 0:
                if action == "on":
                    global man_job
                    if zones[0]['on'] or zones[1]['on'] or zones[2]['on']:
                        templateData['messages'] = "Program Running"
                    else:
                        if length != "0":
                            turn_on(change_pin)
                            templateData['message'] = "Turned " + zones[int(change_pin)]['name'] + " on for " \
                                                      + length + " minutes."
                            temp = datetime.now() + timedelta(seconds=int(length)*60)
                            man_job = sched.add_date_job(turn_off, temp, [change_pin])
                        else:
                            turn_on(change_pin)
                            templateData['message'] = "Turned " + zones[int(change_pin)]['name'] + " on."
                            write_log('%s - Manually turned %s on.\n' % (
                                datetime.now().strftime('%m/%d/%Y %I:%M %p'), zones[int(change_pin)]['name']))
                if action == "off":
                    turn_off(change_pin)
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
            job = sched.add_date_job(sprinkler_go, time_to_start)
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
    os.rename("errors.log", "errors.log.old")
    if on_pi:
        GPIO.setup(7, GPIO.IN)
        GPIO.setup(11, GPIO.IN)
        GPIO.setup(13, GPIO.IN)
