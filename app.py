from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.secret_key = 'supersecretkey'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

RAZORPAY_KEY = 'rzp_test_tBShEJdYWLgAzr'     # replace with actual key
RAZORPAY_SECRET = 'ymsNG0fQ9yE9onZ88JFHFGZ9'  # replace with actual secret

NOTES =  ['SQL', 'DBMS', 'HTML,CSS,JS', 'CN', 'Python', 'OS', 'Java']

# ------------------ Database Init ------------------
def init_db():
    with sqlite3.connect('database.db') as con:
        con.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )''')
        con.execute('''CREATE TABLE IF NOT EXISTS subscriptions (
            user_id INTEGER,
            note_name TEXT,
            access_until TEXT
        )''')

init_db()

# ------------------ User Loader ------------------
class User(UserMixin):
    def __init__(self, id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

# ------------------ Routes ------------------
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        with sqlite3.connect('database.db') as con:
            try:
                con.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
                con.commit()
                return redirect(url_for('login'))
            except:
                return 'User already exists'
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        with sqlite3.connect('database.db') as con:
            cur = con.cursor()
            cur.execute('SELECT id, password FROM users WHERE username = ?', (username,))
            user = cur.fetchone()
            if user and check_password_hash(user[1], password):
                login_user(User(user[0]))
                return redirect(url_for('dashboard'))
            else:
                return 'Invalid credentials'
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    user_id = int(session['_user_id'])
    access_dict = {}

    with sqlite3.connect('database.db') as con:
        cur = con.cursor()
        for note in NOTES:
            cur.execute('SELECT access_until FROM subscriptions WHERE user_id=? AND note_name=?', (user_id, note))
            row = cur.fetchone()
            if row:
                access_date = datetime.strptime(row[0], '%Y-%m-%d')
                remaining = (access_date - datetime.now()).days
                if remaining > 0:
                    access_dict[note] = f"{remaining} days left"
                else:
                    access_dict[note] = "Expired"
            else:
                access_dict[note] = "Locked"

    return render_template('dashboard.html', access=access_dict, notes=NOTES)

@app.route('/payment')
@login_required
def payment():
    note_name = request.args.get('note')
    return render_template('payment.html', key_id=RAZORPAY_KEY, note_name=note_name)

@app.route('/verify_payment', methods=['POST'])
@login_required
def verify_payment():
    data = request.get_json()
    note = data['note_name']
    access_until = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    user_id = int(session['_user_id'])

    with sqlite3.connect('database.db') as con:
        con.execute('INSERT INTO subscriptions (user_id, note_name, access_until) VALUES (?, ?, ?)',
                    (user_id, note, access_until))
        con.commit()

    return jsonify({'message': f'Successfully purchased access to {note}!'})

@app.route('/notes/<note_name>')
@login_required
def notes(note_name):
    note_file_path = os.path.join('static', 'notes', f'{note_name}.pdf')
    if os.path.exists(note_file_path):
        return render_template('view_note.html', note_name=note_name)
    else:
        return 'Note not found', 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)  # Updated to allow access from other devices
