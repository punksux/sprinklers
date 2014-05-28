from flask import Flask, render_template, request, flash, redirect, url_for


# Initialize the Flask application
app = Flask(__name__)

# Set session secret key
app.secret_key = 'some_secret'

# Route '/' and '/index' to `index`
@app.route('/')
def index():
    # Render template
    return render_template('index2.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['username'] != 'admin' or \
                request.form['password'] != 'secret':
            # Login error, flash message
            flash('Invalid credentials')
        else:
            # Login successfully, flash message
            flash('You were successfully logged in')
            return redirect(url_for('index'))
    return render_template('login.html')

# Run
if __name__ == '__main__':
    app.run()
