try:
    with open('settings.ini') as f:
        content = f.readlines()
    for i in range(0, 9):
        a = content[i].rstrip('\r\n')
except (OSError, IndexError):
    content = ['3', '22:00', '40', '40', '30', '1980-1-1 01:01:01', '0', 'False', 'False']
    f = open('settings.ini', 'w')
    for i in content:
        f.write('%s\n' % i)
    f.close()
# ini settings - days apart, time to start, zone 1 length, zone 2 length, zone 3 length, next run date, rain total, full auto, system running


# Settings
on = True
location = "84123"
on_pi = False
weather_test = 0.05
zones = [
    {'length': int(content[2].rstrip('\r\n')), 'on': False, 'pinNo': 7, 'name': 'Zone 1', 'man_timer':False},
    {'length': int(content[3].rstrip('\r\n')), 'on': False, 'pinNo': 11, 'name': 'Zone 2', 'man_timer':False},
    {'length': int(content[4].rstrip('\r\n')), 'on': False, 'pinNo': 13, 'name': 'Zone 3', 'man_timer':False},
]
templateData = {
    'days': int(content[0].rstrip('\r\n')),
    'zones': zones,
    'rain': 0.0,
    'rain_total': float(content[6].rstrip('\r\n')),
    'time_to_start': str(content[1].rstrip('\r\n')),
    'time_to_start_display': 0,
    'message': '',
    'system_running': str(content[8].rstrip('\r\n')),
    'log': {},
    'next_run_date': '',
    'cycle_count': 0,
    'uptime': '',
    'full_auto': str(content[7].rstrip('\r\n'))
}

templateData['full_auto'] = True if templateData['full_auto'] == 'True' else False


forecast = []

# Imports
from flask import Flask, request, render_template, jsonify
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
import random

templateData['time_to_start_display'] = datetime.strptime(templateData['time_to_start'], '%H:%M').strftime('%I:%M %p').lstrip('0')

# Set up Flask
app = Flask(__name__)


# Setup
job = None
cycle_running = False
cycle_has_run = False
uptime_start = datetime.now()

# Set up logging
if on_pi:
    file = open('errors.log', 'w')
    file.close()
    logging.basicConfig(filename='errors.log', level=logging.ERROR, format='%(asctime)s - %(levelname)s: %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')

#Set platform
logging.info("** Running on " + platform.uname()[0] + " **")
if platform.uname()[0] != 'Windows':
    on_pi = True

sched = Scheduler()
sched.start()

if on_pi:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BOARD)

# Get weather
time_checked = datetime.now() - timedelta(days=1)


def check_weather():
    global time_checked, forecast, f
    time_since_last_check = datetime.now() - time_checked
    if weather_test == 100:
        try:
            f = urlopen('http://192.168.1.97:88/weather.json', timeout=5)
            json_string = f.read()
            parsed_json = json.loads(json_string.decode("utf8"))
            f.close()
            templateData['rain'] = parsed_json['rain']
            forecast = parsed_json['forecast']
        except urllib.error.URLError:
            if time_since_last_check.total_seconds() > (10 * 60):
                global something_wrong
                weather_website = ('http://api.wunderground.com/api/c5e9d80d2269cb64/conditions/forecast10day/q/%s.json' % location)
                try:
                    f = urlopen(weather_website, timeout=3)
                    something_wrong = False
                except urllib.error.URLError as e:
                    logging.error('%s - Data not retrieved because %s' % datetime.now().strftime('%m/%d/%Y %I:%M %p'), e)
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
                    with open('weather.json', 'w') as outfile:
                        json.dump(parsed_json, outfile)
                    if parsed_json['current_observation']['precip_today_in'] == '':
                        templateData['rain'] = 0.0
                    else:
                        templateData['rain'] = float(parsed_json['current_observation']['precip_today_in'])

                    for i in range(1, 6):
                        forecast.append([parsed_json['forecast']['simpleforecast']['forecastday'][i]['pop'],
                                         parsed_json['forecast']['simpleforecast']['forecastday'][i]['high']['fahrenheit']])

                time_checked = datetime.now()
    else:
        templateData['rain'] = float(weather_test)
        forecast = [[random.randint(0, 100), random.randint(0, 110)], [random.randint(0, 100), random.randint(0, 110)], [random.randint(0, 100), random.randint(0, 110)], [random.randint(0, 100), random.randint(0, 110)], [random.randint(0, 100), random.randint(0, 110)]]

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
    if (time_to_start - datetime.now()).total_seconds() < 0:
        time_to_start = datetime.now().replace(hour=int(splits[0]), minute=int(splits[1]), second=00, microsecond=0)
    if (time_to_start - datetime.now()).total_seconds() < 0:
        time_to_start = (datetime.now() + timedelta(days=1)).replace(hour=int(splits[0]), minute=int(splits[1]),
                                                                     second=00, microsecond=0)
    print(time_to_start)
    write_settings(5, time_to_start)
    return time_to_start


def get_next_time(dt):
    splits = templateData['time_to_start'].split(":")
    next_time = (dt + timedelta(days=templateData['days']))
    next_time = next_time.replace(hour=int(splits[0]), minute=int(splits[1]), second=00, microsecond=0)
    write_settings(5, next_time.strftime('%Y-%m-%d %H:%M:%S'))
    set_next_run(next_time)
    return next_time


def set_next_run(dt):
    templateData['next_run_date'] = dt.strftime('%a, %B %d at %I:%M %p')


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
        f.write(message + '\n')
        f.close()
        nday = tday
    else:
        f = open('log.log', 'a')
        f.write(message + '\n')
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
        time.strptime(tinput, '%I:%M %p')
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
    if templateData['system_running']:
        templateData['rain_total'] = 0.0
    else:
        check_weather()
        try:
            templateData['rain_total'] += float(templateData['rain'])
        except (ValueError, TypeError):
            pass
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


def scheduled_turn_on(i):
    write_log('%s - %s on: %s min.' % (datetime.now().strftime('%m/%d/%Y %I:%M %p'), zones[i]['name'], zones[i]['length']))
    if on_pi:
        GPIO.output(zones[i]['pinNo'], False)
    else:
        print('%s - %s on: %s min.' % (datetime.now().strftime('%m/%d/%Y %I:%M %p'), zones[i]['name'], zones[i]['length']))
    zones[i]['on'] = True


def scheduled_turn_off(i):
    write_log('%s - %s off.' % (datetime.now().strftime('%m/%d/%Y %I:%M %p'), zones[i]['name']))
    if on_pi:
        GPIO.output(zones[i]['pinNo'], True)
    else:
        print('%s - %s off.' % (datetime.now().strftime('%m/%d/%Y %I:%M %p'), zones[i]['name']))
    zones[i]['on'] = False


def schedule_finish(dt):
    global job, cycle_running, cycle_has_run
    if templateData['rain'] > 0:
        for i in range(0, len(zones)):
            zones[i]['length'] = temp_length[i]
    if templateData['full_auto']:
        set_full_auto()
    next_time = get_next_time(dt)
    job = sched.add_date_job(sprinkler_go, next_time)
    cycle_running = False
    templateData['cycle_count'] += 1
    cycle_has_run = True
    templateData['rain_total'] = 0.0
    write_settings(6, templateData['rain_total'])
    templateData['message'] = ''


# Run program
high_rain = 0.2
low_rain = 0.1
temp_length = []


def sprinkler_go():
    global job, cycle_running, cycle_has_run, temp_length
    try:
        check_weather()
        templateData['rain_total'] += float(templateData['rain'])
    except:
        pass

    if float(templateData['rain']) > high_rain or float(templateData['rain_total']) > (int(templateData['days']) * (high_rain / 2)):
        write_log('%s - Canceling for rain ( %s - %s ) - trying again in %s days.' % (datetime.now().strftime('%m/%d/%Y %I:%M %p'), templateData['rain'], templateData['rain_total'], str(templateData['days'])))
        temp = datetime.now() + timedelta(days=int(templateData['days']))
        job = sched.add_date_job(sprinkler_go, temp)
        templateData['next_run_date'] = temp.strftime('%a, %B %d at %I:%M %p')
        templateData['rain_total'] = 0.0
        write_settings(6, templateData['rain_total'])
        write_settings(5, temp.strftime('%Y-%m-%d %H:%M:%S'))
    elif float(templateData['rain_total']) > (int(templateData['days']) * (low_rain / 2)):
        write_log('%s - Canceling for rain ( %s - %s ) - trying again tomorrow.' % (datetime.now().strftime('%m/%d/%Y %I:%M %p'), templateData['rain'], templateData['rain_total']))
        temp = datetime.now() + timedelta(days=1)
        job = sched.add_date_job(sprinkler_go, temp)
        templateData['next_run_date'] = temp.strftime('%a, %B %d at %I:%M %p')
        templateData['rain_total'] = 0.0
        write_settings(6, templateData['rain_total'])
        write_settings(5, temp.strftime('%Y-%m-%d %H:%M:%S'))
    else:
        if templateData['rain'] > 0:
            temp_length = []
            percent = templateData['rain'] / high_rain
            for i in zones:
                r = i['length']
                temp_length.append(r)
                i['length'] -= int(r * percent)
                print(str(i['name']) + ' - ' + str(i['length']))
        cycle_running = True
        templateData['message'] = 'Running Cycle'
        tt = 0
        scheduled_turn_on(0)
        for i in range(0, len(zones)):
            sched.add_date_job(scheduled_turn_off, datetime.now() + timedelta(seconds=(zones[i]['length'] * 60) + tt), name=('zone_off_' + str(i)), args=[i])
            if i + 1 < len(zones):
                sched.add_date_job(scheduled_turn_on, datetime.now() + timedelta(seconds=(zones[i]['length'] * 60) + tt - 5), name=('zone_on_' + str(i + 1)), args=[i + 1])
                tt += zones[i]['length'] * 60
            else:
                sched.add_date_job(schedule_finish, datetime.now() + timedelta(seconds=(zones[i]['length'] * 60) + tt), name='schedule_finish', args=[datetime.now()])


def set_length(add):
    zone1 = 40
    zone2 = 40
    zone3 = 30

    zones[0]['length'] = zone1 + add
    zones[1]['length'] = zone2 + add
    zones[2]['length'] = zone3 + add


def set_full_auto():
    temp = [0, 0, 0, 0]
    rain = [0, 0, 0, 0]
    check_weather()
    for j in range(2, 6):
        for i in range(0, j):
            temp[j - 2] += float(forecast[i][1])
            if float(forecast[i][0]) > rain[j - 2]:
                rain[j - 2] = float(forecast[i][0])
        temp[j - 2] /= j
    if temp[0] > 100:
        templateData['days'] = 2
        set_length(10)
    elif 100 > temp[0] > 90:
        if rain[0] > 60:
            templateData['days'] = 3
        else:
            templateData['days'] = 2
        set_length(0)
    elif 90 > temp[1] > 80:
        if rain[1] > 60:
            templateData['days'] = 4
        else:
            templateData['days'] = 3
        set_length(0)
    elif 80 > temp[2] > 70:
        if rain[2] > 60:
            templateData['days'] = 5
        else:
            templateData['days'] = 4
        set_length(0)
    elif 70 > temp[3] > 60:
        if rain[3] > 60:
            templateData['days'] = 6
        else:
            templateData['days'] = 5
        set_length(0)
    elif temp[3] < 60:
        templateData['days'] = 6
        set_length(-10)


def st_program(st):
    global job
    if st == 'False':
        for i in sched.get_jobs():
            if i.name == 'sprinkler_go':
                sched.unschedule_job(job)
        templateData['system_running'] = False
        templateData['message'] = "System Stopped"
        templateData['next_run_date'] = ''
        write_log('%s - System stopped.' % (datetime.now().strftime('%m/%d/%Y %I:%M %p')))
    else:
        time_to_start = get_start_time()
        set_next_run(time_to_start)
        job = sched.add_date_job(sprinkler_go, time_to_start)
        templateData['system_running'] = True
        templateData['message'] = "System Started"
        write_log('%s - System started.' % (datetime.now().strftime('%m/%d/%Y %I:%M %p')))

st_program(templateData['system_running'])

print('Running')

# Web part
try:

    @app.route('/')
    def my_form():
        templateData['log'] = [log.rstrip('\n') for log in open('log.log')]
        check_weather()
        templateData['uptime'] = time_since(uptime_start)
        return render_template("index.html", **templateData)

    @app.route('/full_auto', methods=['POST'])
    def full_auto():
        full_auto = request.form.get('full_auto', '', type=str)
        if full_auto.title() == 'True':
            templateData['full_auto'] = True
            write_settings(7, True)
        else:
            templateData['full_auto'] = False
            write_settings(7, False)
        return jsonify({'message': templateData['message']})

    @app.route('/apply', methods=['POST'])
    def apply():
        global cycle_has_run, job
        send_message = 0
        days = request.form.get('days', '', type=int)
        ttime = request.form.get('time', '', type=str)
        zone1length = request.form.get('zone1length', '', type=int)
        zone2length = request.form.get('zone2length', '', type=int)
        zone3length = request.form.get('zone3length', '', type=int)
        if days != '':
            templateData['days'] = days
            write_settings(0, days)
            send_message += 1
        if ttime != '':
            if is_time_format(ttime):
                ttime = datetime.strptime(ttime, '%I:%M %p').strftime('%H:%M')
                if cycle_has_run:
                    if templateData['system_running']:
                        sched.unschedule_job(job)
                        templateData['time_to_start'] = str(ttime)
                        write_settings(1, str(ttime))
                        time_to_start = get_start_time()
                        set_next_run(time_to_start)
                        check_weather()
                        job = sched.add_date_job(sprinkler_go, time_to_start)
                    else:
                        templateData['time_to_start'] = str(ttime)
                        write_settings(1, str(ttime))
                else:
                    if templateData['system_running']:
                        sched.unschedule_job(job)
                        templateData['time_to_start'] = str(ttime)
                        write_settings(1, str(ttime))
                        time_to_start = get_start_time()
                        set_next_run(time_to_start)
                        check_weather()
                        job = sched.add_date_job(sprinkler_go, time_to_start)
                    else:
                        templateData['time_to_start'] = str(ttime)
                        write_settings(1, str(ttime))
            else:
                templateData['message'] = 'Error: Incorrect Time'
            send_message += 1
        if zone1length != '':
            zones[0]['length'] = zone1length
            write_settings(2, zone1length)
            send_message += 1
        if zone2length != '':
            zones[1]['length'] = zone2length
            write_settings(3, zone2length)
            send_message += 1
        if zone3length != '':
            zones[2]['length'] = zone3length
            write_settings(4, zone3length)
            send_message += 1
        if send_message > 0:
            templateData['message'] = 'Updated Settings'
        else:
            templateData['message'] = ''
        templateData['uptime'] = time_since(uptime_start)
        return jsonify({'message': templateData['message'], 'nextTime': templateData['next_run_date']})

    @app.route("/manual", methods=['POST'])
    def manual():
        number = request.form.get('number', 'something is wrong', type=int)
        length = request.form.get('length', 'something is wrong', type=str)

        if cycle_running:
            templateData['message'] = 'Cycle Running'
            on_off = 'off'
        else:
            if zones[number]['on'] is False:
                if length != "0":
                    turn_on(number)
                    temp = datetime.now() + timedelta(seconds=int(length) * 60)
                    templateData['message'] = "Turned " + zones[number]['name'] + " on for " + length + " minutes."
                    on_off = 'on'
                    write_log('%s - Manually turned %s on for %s minutes.' % (datetime.now().strftime('%m/%d/%Y %I:%M %p'), zones[number]['name'], length))
                    zones[number]['man_timer'] = True
                    sched.add_date_job(turn_off, temp, args=[number], name='job' + str(number))
                else:
                    turn_on(number)
                    templateData['message'] = "Turned " + zones[number]['name'] + " on."
                    write_log('%s - Manually turned %s on.' % (datetime.now().strftime('%m/%d/%Y %I:%M %p'), zones[number]['name']))
                    on_off = 'on'
            else:
                turn_off(number)
                templateData['message'] = "Turned " + zones[number]['name'] + " off."
                write_log('%s - Manually turned %s off.' % (datetime.now().strftime('%m/%d/%Y %I:%M %p'), zones[number]['name']))
                on_off = 'off'
                if zones[number]['man_timer']:
                    for i in sched.get_jobs():
                        if i.name == 'job' + str(number):
                            sched.unschedule_job(i)

        return jsonify({'message': templateData['message'], 'onOff': on_off})

    @app.route("/start_stop", methods=['POST'])
    def start_program():
        global job
        start_stop = request.form.get('start_stop', '', type=str)
        if start_stop == 'stop':
            for i in sched.get_jobs():
                if i.name == 'sprinkler_go':
                    sched.unschedule_job(job)
            templateData['system_running'] = False
            write_settings(8, False)
            templateData['message'] = "System Stopped"
            templateData['next_run_date'] = ''
            write_log('%s - System stopped.' % (datetime.now().strftime('%m/%d/%Y %I:%M %p')))
            start_stop = 'start'
        else:
            time_to_start = get_start_time()
            set_next_run(time_to_start)
            job = sched.add_date_job(sprinkler_go, time_to_start)
            templateData['system_running'] = True
            write_settings(8, True)
            templateData['message'] = "System Started"
            write_log('%s - System started.' % (datetime.now().strftime('%m/%d/%Y %I:%M %p')))
            start_stop = 'stop'
        return jsonify({'message': templateData['message'], 'sysRunning': start_stop, 'nextRunDate': templateData['next_run_date']})

    @app.route('/log', methods=['POST'])
    def get_log():
        logs = [log.rstrip('\n') for log in open('log.log')]
        if len(logs) > 13:
            logs = logs[len(logs) - 13:]

        return jsonify({'log': logs})

    @app.route('/uptime', methods=['POST'])
    def get_uptime_count():
        templateData['uptime'] = time_since(uptime_start)
        return jsonify({'uptime': templateData['uptime'], 'count': templateData['cycle_count'], 'next': templateData['next_run_date'], 'rain': templateData['rain'], 'rainTotal': templateData['rain_total']})

    if __name__ == '__main__':
        app.run(host='0.0.0.0', port='5001')

finally:
    print("Quitting...")
    print('Shutting Down Scheduler...')
    sched.shutdown(wait=False)
    print("Reseting GPIO Pins...")
    if on_pi:
        GPIO.setup(7, GPIO.IN)
        GPIO.setup(11, GPIO.IN)
        GPIO.setup(13, GPIO.IN)
    print("Rename Error File...")
    try:
        os.remove("errors.log.old")
        os.rename("errors.log", "errors.log.old")
    except FileNotFoundError:
        pass
    print("Done.")