from flask import Flask, request, render_template, url_for, flash, redirect
import time
from threading import Thread

app = Flask(__name__)

templateData = {
   'days' : 3,
   'zone1' : {'length':40,'on':False},
   'zone2' : {'length':30,'on':False},
   'zone3' : {'length':30,'on':False},
   }

##def print_stuff():
##    while True:
##        print (templateData['no'])
##        time.sleep (5)
##
##
##thread = Thread(target = print_stuff)
##thread.start()

@app.route('/')
def my_form():
    return render_template("index.html", **templateData)

@app.route('/', methods=['POST'])
def my_form_post():
    text = request.form['text']
    zone1 = request.form['zone1']
    zone2 = request.form['zone2']
    zone3 = request.form['zone3']
    if text != '':
        templateData['days'] = str(text)
    if zone1 != '':
        templateData['zone1']['length'] = int(zone1)
    if zone2 != '':
        templateData['zone2']['length'] = int(zone2)
    if zone3 != '':
        templateData['zone3']['length'] = int(zone3)    
    return render_template("index.html", **templateData)

@app.route("/<changePin>/<action>")
def action(changePin, action):
    if action == "on":
        templateData[changePin]['on'] = True
        #flash("Turned " + changePin + " on.")
    if action == "off":
        templateData[changePin]['on'] = False
        #message = "Turned " + changePin + " off."
    if action == "toggle":
        templateData[changePin]['on'] = not teplateData['changePin']['on']
        #message = "Toggled " + changePin + "."
    return redirect(url_for('my_form'))
    
if __name__ == '__main__':
    app.run(debug=True)




