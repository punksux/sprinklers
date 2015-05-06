try:
    with open('settings.ini') as f:
        content = f.readlines()
    for i in range(0, 7):
        a = content[i].rstrip('\r\n')
except:
    content = ['3', '22:00', '40', '40', '30', '1980-1-1 01:01:01', '0']
    f = open('settings.ini', 'w')
    for i in content:
        f.write('%s\n' % i)
    f.close()

# Settings
on = True
location = "84123"
on_pi = False
weather_test = 70
zones = [
    {'length': int(content[2].rstrip('\r\n')), 'on': False, 'pinNo': 7, 'name': 'Zone 1', 'man_timer':False},
    {'length': int(content[3].rstrip('\r\n')), 'on': False, 'pinNo': 11, 'name': 'Zone 2', 'man_timer':False},
    {'length': int(content[4].rstrip('\r\n')), 'on': False, 'pinNo': 13, 'name': 'Zone 3', 'man_timer':False},
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
    'uptime': '',
    'full_auto': False
}

forecast = []

# Imports
from flask import Flask, request, render_template, url_for, redirect, jsonify
from datetime import datetime, timedelta
import time
import os
import platform
from apscheduler.scheduler import Scheduler
from socket import timeout
import logging
import logging.handlers
from urllib.request import urlopen
import urllib.error
import json

# Set up Flask
app = Flask(__name__)

# Setup
job = None
cycle_running = False
cycle_has_run = False
uptime_start = datetime.now()

# Set up logging
# open('errors.log', 'w').close()
# logging.basicConfig(filename='errors.log', level=logging.ERROR, format='%(asctime)s - %(levelname)s: %(message)s',
#                     datefmt='%m/%d/%Y %I:%M:%S %p')

#Set platform
logging.info("** Running on " + platform.uname()[0] + " **")
if platform.uname()[0] != 'Windows':
    on_pi = True

sched = Scheduler()
sched.start()

if on_pi:
    import RPi.GPIO as GPIO

# Get weather
time_checked = datetime.now() - timedelta(days=1)


def check_weather():
    global time_checked, forecast, f
    time_since_last_check = datetime.now() - time_checked
    if weather_test == 100:
        try:
            f = urlopen('192.168.1.97:88/weather.json', timeout=5)
            json_string = f.read()
            parsed_json = json.loads(json_string.decode("utf8"))
            f.close()
            templateData['rain'] = parsed_json['rain']
            forecast = parsed_json['forecast']
        except:
            if time_since_last_check.total_seconds() > (10 * 60):
                global something_wrong
                weather_website = (
                'http://api.wunderground.com/api/c5e9d80d2269cb64/conditions/forecast10day/q/%s.json' % location)
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
                    f.close()
                    templateData['rain'] = parsed_json['current_observation']['precip_today_in']

                    for i in range(1, 4):
                        forecast.append([parsed_json['forecast']['simpleforecast']['forecastday'][i]['pop'],
                                         parsed_json['forecast']['simpleforecast']['forecastday'][i]['high'][
                                             'fahrenheit']])

                time_checked = datetime.now()
    else:
        templateData['rain'] = weather_test
        forecast = [['30', '75'], ['0', '80'], ['75', '65']]

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
    global job
    check_weather()
    templateData['rain_total'] += float(templateData['rain'])
    print(datetime.now())

    if float(templateData['rain']) > 0.2 or float(templateData['rain_total']) > (int(templateData['days']) * .125):
        write_log('%s - Canceling for rain - trying again in %s days.\n' %
                  (datetime.now().strftime('%m/%d/%Y %I:%M %p'), str(templateData['days'])))
        temp = datetime.now() + timedelta(days=int(templateData['days']))
        job = sched.add_date_job(sprinkler_go, temp)
        templateData['next_run_date'] = temp.strftime('%a, %B %d at %I:%M %p')
        templateData['rain_total'] = 0.0
        write_settings(6, templateData['rain_total'])
    elif float(templateData['rain']) > 0.1 or float(templateData['rain_total']) > (int(templateData['days']) * .063):
        write_log('%s - Canceling for rain - trying again tomorrow.\n' % (datetime.now().strftime('%m/%d/%Y %I:%M %p')))
        temp = datetime.now() + timedelta(days=1)
        job = sched.add_date_job(sprinkler_go, temp)
        templateData['next_run_date'] = temp.strftime('%a, %B %d at %I:%M %p')
        templateData['rain_total'] = 0.0
        write_settings(6, templateData['rain_total'])
    else:
        global cycle_running, cycle_has_run, next_time
        cycle_running = True
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
        cycle_running = False
        templateData['cycle_count'] += 1
        cycle_has_run = True
        templateData['rain_total'] = 0.0
        write_settings(6, templateData['rain_total'])
        templateData['message'] = ''


print('Running')

# Web part
try:

    @app.route('/')
    def my_form():
        templateData['log'] = [log.rstrip('\n') for log in open('log.log')]
        check_weather()
        templateData['uptime'] = time_since(uptime_start)
        return render_template("index.html", **templateData)

    @app.route('/', methods=['POST'])
    def my_form_post():
        text = request.form['text']
        ttime = request.form['start']
        zone1 = request.form['run0']
        zone2 = request.form['run1']
        zone3 = request.form['run2']
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
                        time_to_start = get_start_time()
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
        templateData['uptime'] = time_since(uptime_start)
        return render_template("index.html", **templateData)

    @app.route("/manual", methods=['POST'])
    def action():
        on_off = 'on'
        number = request.form.get('number', 'something is wrong', type=int)
        length = request.form.get('length', 'something is wrong', type=str)
        print(str(number) + ' - ' + str(length))

        if cycle_running:
            templateData['message'] = 'Cycle Running'
        else:
            if zones[number]['on'] is False:
                if length != "0":
                    turn_on(number)
                    temp = datetime.now() + timedelta(seconds=int(length) * 60)
                    templateData['message'] = "Turned " + zones[number]['name'] + " on for " + length + " minutes."
                    on_off = 'on'
                    write_log('%s - Manually turned %s on for %s minutes.\n' % (datetime.now().strftime('%m/%d/%Y %I:%M %p'), zones[number]['name'], length))
                    zones[number]['man_timer'] = True
                    sched.add_date_job(turn_off, temp, args=[number], name='job' + str(number))
                else:
                    turn_on(number)
                    templateData['message'] = "Turned " + zones[number]['name'] + " on."
                    write_log('%s - Manually turned %s on.\n' % (datetime.now().strftime('%m/%d/%Y %I:%M %p'), zones[number]['name']))
                    on_off = 'on'
            else:
                turn_off(number)
                templateData['message'] = "Turned " + zones[number]['name'] + " off."
                write_log('%s - Manually turned %s off.\n' % (datetime.now().strftime('%m/%d/%Y %I:%M %p'), zones[number]['name']))
                on_off = 'off'
                if zones[number]['man_timer']:
                    for i in sched.get_jobs():
                        if i.name == 'job' + str(number):
                            sched.unschedule_job(i)

        return jsonify({'message': templateData['message'], 'onOff': on_off})


    @app.route("/start", methods=['POST'])
    def start_program():
        if templateData['system_running'] is False:
            time_to_start = get_start_time()
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
    sched.shutdown(wait=False)
    os.rename("errors.log", "errors.log.old")
    if on_pi:
        GPIO.setup(7, GPIO.IN)
        GPIO.setup(11, GPIO.IN)
        GPIO.setup(13, GPIO.IN)
