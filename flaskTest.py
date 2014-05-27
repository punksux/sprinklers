from flask import Flask
from flask import request
from flask import render_template
import time
from threading import Thread

app = Flask(__name__)

no = "Poo"

def print_stuff():
    while True:
        print (no)
        time.sleep (1)


thread = Thread(target = print_stuff)
thread.start()

@app.route('/')
def my_form():
    return render_template("index.html", **no)

@app.route('/', methods=['POST'])
def my_form_post():

    text = request.form['text']
    global no
    no = str(text)
    processed_text = text.upper()
    return processed_text

if __name__ == '__main__':
    app.run()




