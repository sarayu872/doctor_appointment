from flask import Flask, request, render_template, session, redirect, url_for
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = "your_secret_key_12345"  # Change in production

# ====================== DATABASE ======================
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient TEXT NOT NULL,
            doctor TEXT NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            problem TEXT,
            symptoms TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# ====================== HELPERS ======================
def time_to_minutes(t):
    h, m = map(int, t.split(':'))
    return h * 60 + m

def minutes_to_time(m):
    h = m // 60
    m = m % 60
    return f"{h:02d}:{m:02d}"

# ====================== ROUTES ======================

@app.route('/')
def index():
    return redirect(url_for('login'))

# ------------------- LOGIN -------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        role = request.form.get('role', '').strip()
        password = request.form.get('password', '').strip()

        if not role:
            return '<script>alert("Please select a role."); window.location="/login"</script>'

        if role == 'doctor' and password == 'doc1234':
            session['role'] = 'doctor'
            return redirect(url_for('doctor_dashboard'))
        elif role == 'admin' and password == 'adm1234':
            session['role'] = 'admin'
            return redirect(url_for('admin_dashboard'))
        elif role == 'patient':
            session['role'] = 'patient'
            return redirect(url_for('patient_dashboard'))
        else:
            return '<script>alert("Invalid role or password."); window.location="/login"</script>'

    return render_template('login.html')

# ------------------- DOCTOR DASHBOARD -------------------
@app.route('/doctor')
def doctor_dashboard():
    if session.get('role') != 'doctor':
        return redirect(url_for('login'))

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT id, patient, doctor, date, time, problem, symptoms FROM appointments")
    appointments = c.fetchall()
    conn.close()

    return render_template('index.html', appointments=appointments, role='doctor')

# ------------------- ADMIN DASHBOARD -------------------
@app.route('/admin')
def admin_dashboard():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT id, patient, doctor, date, time, problem, symptoms FROM appointments")
    appointments = c.fetchall()
    conn.close()

    return render_template('index.html', appointments=appointments, role='admin')

# ------------------- PATIENT DASHBOARD (BOOKING) -------------------
@app.route('/patient', methods=['GET', 'POST'])
def patient_dashboard():
    if session.get('role') != 'patient':
        return redirect(url_for('login'))

    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    if request.method == 'POST':
        patient = request.form['patientName'].strip()
        doctor = request.form['doctor']
        date = request.form['date']
        time = request.form['time']
        problem = request.form['problem'].strip()
        symptoms = request.form['symptoms'].strip()

        if not all([patient, doctor, date, time, problem, symptoms]):
            return '<script>alert("Please fill all fields."); window.location="/patient"</script>'

        # Validate date
        try:
            appt_date = datetime.strptime(date, '%Y-%m-%d').date()
            if appt_date < datetime.now().date():
                return '<script>alert("Cannot book past dates."); window.location="/patient"</script>'
        except:
            return '<script>alert("Invalid date format."); window.location="/patient"</script>'

        # === 1-HOUR GAP CHECK ===
        try:
            requested_minutes = time_to_minutes(time)
        except:
            return '<script>alert("Invalid time format."); window.location="/patient"</script>'

        c.execute("SELECT time FROM appointments WHERE doctor = ? AND date = ?", (doctor, date))
        booked_times = c.fetchall()

        for (booked_time,) in booked_times:
            booked_minutes = time_to_minutes(booked_time)
            diff = abs(requested_minutes - booked_minutes)
            if diff < 60:  # Within 1 hour
                start = minutes_to_time(booked_minutes - 30)
                end = minutes_to_time(booked_minutes + 30)
                return f'<script>alert("Doctor is busy from {start} to {end}. Please choose another time."); window.location="/patient"</script>'

        # === BOOK APPOINTMENT ===
        c.execute("""
            INSERT INTO appointments (patient, doctor, date, time, problem, symptoms)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (patient, doctor, date, time, problem, symptoms))
        conn.commit()
        return '<script>alert("Appointment booked successfully!"); window.location="/patient"</script>'

    # Show all appointments
    c.execute("SELECT id, patient, doctor, date, time, problem, symptoms FROM appointments")
    appointments = c.fetchall()
    conn.close()

    return render_template('index.html', appointments=appointments, role='patient')

# ------------------- LOGOUT -------------------
@app.route('/logout')
def logout():
    session.pop('role', None)
    return redirect(url_for('login'))

# ------------------- DELETE (ADMIN) -------------------
@app.route('/delete/<int:id>')
def delete(id):
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("DELETE FROM appointments WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return '<script>window.location="/admin"</script>'

# ====================== RUN ======================
if __name__ == '__main__':
    app.run(debug=True)