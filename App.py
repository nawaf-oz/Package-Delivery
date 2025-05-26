from flask import Flask, render_template, request, redirect, url_for, flash
import psycopg2
import hashlib
from datetime import datetime
import random
app = Flask(__name__)
app.secret_key = '****'
DATABASE_URL = "****"
def get_db():
    return psycopg2.connect(DATABASE_URL)
def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()
@app.route('/')
def home():
    return render_template('signup.html')
@app.route('/signup', methods=['POST'])
def signup():
    role = request.form['user_class']
    email = request.form['email']
    pw = request.form['password']
    fname = request.form['fname']
    lname = request.form['lname']
    phone = request.form['phone']

    if len(pw) < 6:
        flash("Password must be at least 6 characters.")
        return redirect(url_for('home'))

    if role == 'Faculty':
        if not email.endswith('@ksu.edu.sa'):
            flash("Faculty must use their @ksu.edu.sa")
            return redirect(url_for('home'))
        sid = email
    elif role == 'Courier':
        sid = email
    elif role == 'Student':
        sid = request.form['sid']
        if len(sid) != 9 or not sid.isdigit():
            flash("Student ID must be exactly 9 digits.")
            return redirect(url_for('home'))
        if not email.endswith('@student.ksu.edu.sa'):
            flash("Students must use their @student.ksu.edu.sa")
            return redirect(url_for('home'))
    else:
        flash("Invalid role.")
        return redirect(url_for('home'))

    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE id = %s", (sid,))
        if c.fetchone():
            flash("User already registered.")
            return redirect(url_for('home'))

        c.execute('''
            INSERT INTO users (id, first_name, last_name, email, phone, password_hash, user_class)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (sid, fname, lname, email, phone, hash_password(pw), role))
        conn.commit()
        flash(f'Registration successful! Welcome {role} {sid}')
    except Exception as e:
        conn.rollback()
        flash(f'Database Error: {e}')
    finally:
        conn.close()

    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        role = request.form['user_class']
        pw = hash_password(request.form['password'])
        sid = request.form['sid']

        if role == 'Student':
            if len(sid) != 9 or not sid.isdigit():
                flash('Student ID must be 9 digits.')
                return redirect(url_for('login'))
        elif role == 'Faculty':
            if not sid.endswith('@ksu.edu.sa'):
                flash('Faculty must use their @ksu.edu.sa')
                return redirect(url_for('login'))
        elif role == 'Courier':
            pass  # Courier can use any email
        else:
            flash("Invalid role.")
            return redirect(url_for('login'))

        try:
            conn = get_db()
            c = conn.cursor()
            c.execute('SELECT password_hash, user_class FROM users WHERE id=%s', (sid,))
            row = c.fetchone()
            conn.close()

            if row and row[0] == pw:
                flash(f'Login successful! Welcome')
                if row[1] == 'Courier':
                    return redirect(url_for('courier_dashboard', uid=sid))
                else:
                    return redirect(url_for('dashboard', role=row[1], uid=sid))
            else:
                flash('Login failed. Check your ID or password.')
        except Exception as e:
            flash(f"Login error: {e}")

    return render_template('login.html')

@app.route('/dashboard/<role>/<uid>', methods=['GET', 'POST'])
def dashboard(role, uid):
    offices = ['Riyadh Main', 'KSU Central', 'Airport Depot', 'Al Nakheel Office']
    packages = []
    try:
        conn = get_db()
        c = conn.cursor()
        if request.method == 'POST':
            office = request.form['office']
            dimensions = request.form['dimensions']
            weight = request.form['weight']
            receiver = request.form['receiver']
            if not all([office, dimensions, weight, receiver]):
                flash("All fields are required.")
            else:
                track_id = ''.join([str(random.randint(0, 9)) for _ in range(16)])
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                c.execute('''
                    INSERT INTO packages (sender_id, receiver_id, office, dimensions, weight, track_id, timestamp, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, 'Dropped')
                ''', (uid, receiver, office, dimensions, weight, track_id, timestamp))
                conn.commit()
                flash(f"Package submitted! Tracking #: {track_id}")
        c.execute("SELECT * FROM packages WHERE sender_id = %s ORDER BY timestamp DESC", (uid,))
        packages = c.fetchall()
    except Exception as e:
        flash(f"Dashboard Error: {e}")
    finally:
        conn.close()
    return render_template('dashboard.html', role=role, user_id=uid, packages=packages, offices=offices)
@app.route('/courier/<uid>', methods=['GET', 'POST'])
def courier_dashboard(uid):
    if request.method == 'POST':
        action = request.form['action']
        sender_id = request.form['sender_id']
        track_id = request.form['track_id']
        if not sender_id or not track_id or len(track_id) != 16:
            flash("Sender ID and valid 16-digit Tracking Number are required.")
            return redirect(url_for('courier_dashboard', uid=uid))
        try:
            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT * FROM packages WHERE sender_id=%s AND track_id=%s", (sender_id, track_id))
            pkg = c.fetchone()
            if not pkg:
                flash("Package not found.")
            else:
                new_status = 'Accepted' if action == 'accept' else 'Delivered'
                c.execute("UPDATE packages SET status=%s WHERE sender_id=%s AND track_id=%s",
                          (new_status, sender_id, track_id))
                conn.commit()
                flash(f"Package status updated to {new_status}")
        except Exception as e:
            flash(f"Error updating package: {e}")
        finally:
            conn.close()
    return render_template('courier_dashboard.html', courier_id=uid)
with get_db() as conn:
    with conn.cursor() as c:
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                first_name TEXT,
                last_name TEXT,
                email TEXT,
                phone TEXT,
                password_hash TEXT,
                user_class TEXT
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS packages (
                id SERIAL PRIMARY KEY,
                sender_id TEXT,
                receiver_id TEXT,
                office TEXT,
                dimensions TEXT,
                weight TEXT,
                track_id TEXT,
                timestamp TEXT,
                status TEXT
            )
        ''')
        conn.commit()
if __name__ == '__main__':
    app.run(debug=True)
    #cd IS324
    #python App.py
