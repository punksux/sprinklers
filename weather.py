
import urllib2
import json
f = urllib2.urlopen('http://api.wunderground.com/api/c5e9d80d2269cb64/geolookup/conditions/forecast/q/84123.json')
json_string = f.read()
parsed_json = json.loads(json_string)
location = parsed_json['location']['city']
temp_f = parsed_json['current_observation']['temp_f']
rain = parsed_json['current_observation']['precip_today_in']
#rain_tom = parsed_json['
print "Current temperature in %s is: %s with %s inches of rain." % (location, temp_f, rain)
print (parsed_json['forecast']['txt_forecast']['forecastday'][1]['fcttext'])
if float(rain) > 0.125:
    print('No sprinkling today')
else:
    print('go')
f.close()
