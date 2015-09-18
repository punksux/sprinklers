from urllib.request import urlopen
import json

with open('test.json') as json_string:
    parsed_json = json.load(json_string)

print(parsed_json)
print(parsed_json["history"]["dailysummary"][0]["precipi"])
