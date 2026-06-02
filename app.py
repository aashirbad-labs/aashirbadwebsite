from datetime import datetime, date, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import logging
from dotenv import load_dotenv
import re

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'office_secret_key')
app.config['WTF_CSRF_ENABLED'] = True
app.config['WTF_CSRF_TIME_LIMIT'] = None
csrf = CSRFProtect(app)
limiter = Limiter(app=app, key_func=get_remote_address, default_limits=["200 per day", "50 per hour"])

# Ensure database is initialized on startup
_db_initialized = False

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('app.log'), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

DB_PATH = os.environ.get('DB_PATH', 'employees.db')
VIDEO_DIR = os.path.join('static', 'checkin_videos')
VIDEO_MAX_AGE_DAYS = int(os.environ.get('VIDEO_MAX_AGE_DAYS', 30))
ALLOWED_VIDEO_EXTENSIONS = {'webm', 'mp4', 'ogg'}
MIN_PASSWORD_LENGTH = 8

# Database helpers
def get_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise


def init_db():
    with get_db() as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id TEXT UNIQUE,
                password TEXT,
                name TEXT,
                contact TEXT,
                gmail TEXT,
                address TEXT,
                postal_code TEXT,
                dob TEXT,
                is_admin INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id TEXT,
                date TEXT,
                check_in TEXT,
                check_out TEXT,
                video_path TEXT,
                UNIQUE(employee_id, date),
                FOREIGN KEY(employee_id) REFERENCES employees(employee_id)
            )
        ''')
        conn.commit()
        
        # Migrate attendance table if needed
        c.execute("PRAGMA table_info(attendance)")
        columns = [row[1] for row in c.fetchall()]
        if 'video_path' not in columns:
            c.execute('ALTER TABLE attendance ADD COLUMN video_path TEXT')
            conn.commit()
            logger.info("Added video_path column to attendance table")
        
        # Migrate employees table if needed
        c.execute("PRAGMA table_info(employees)")
        columns = [row[1] for row in c.fetchall()]
        if 'is_admin' not in columns:
            c.execute('ALTER TABLE employees ADD COLUMN is_admin INTEGER DEFAULT 0')
            conn.commit()
            logger.info("Added is_admin column to employees table")
        if 'created_at' not in columns:
            c.execute('ALTER TABLE employees ADD COLUMN created_at TIMESTAMP')
            conn.commit()
            logger.info("Added created_at column to employees table")
        
        # Create indexes for performance
        try:
            c.execute('CREATE INDEX IF NOT EXISTS idx_employee_id ON attendance(employee_id)')
            c.execute('CREATE INDEX IF NOT EXISTS idx_date ON attendance(date)')
            c.execute('CREATE INDEX IF NOT EXISTS idx_emp_date ON attendance(employee_id, date)')
            conn.commit()
            logger.info("Created database indexes")
        except Exception as e:
            logger.warning(f"Index creation warning: {e}")
        
        os.makedirs(VIDEO_DIR, exist_ok=True)
        cleanup_old_videos()


def get_employee_by_id(employee_id):
    with get_db() as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM employees WHERE employee_id = ?', (employee_id,))
        return c.fetchone()


def get_today_attendance(employee_id):
    today = date.today().isoformat()
    with get_db() as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM attendance WHERE employee_id = ? AND date = ?', (employee_id, today))
        return c.fetchone()


def allowed_video_filename(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_VIDEO_EXTENSIONS


def is_valid_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def is_strong_password(password):
    if len(password) < MIN_PASSWORD_LENGTH:
        return False, f"Password must be at least {MIN_PASSWORD_LENGTH} characters"
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r'[0-9]', password):
        return False, "Password must contain at least one digit"
    return True, "Password is strong"


def cleanup_old_videos():
    threshold = datetime.now() - timedelta(days=VIDEO_MAX_AGE_DAYS)
    for filename in os.listdir(VIDEO_DIR):
        filepath = os.path.join(VIDEO_DIR, filename)
        if not os.path.isfile(filepath):
            continue
        file_mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
        if file_mtime < threshold:
            try:
                os.remove(filepath)
            except OSError:
                pass


def get_attendance_history(employee_id, limit=10):
    with get_db() as conn:
        c = conn.cursor()
        c.execute('''
            SELECT date, check_in, check_out
            FROM attendance
            WHERE employee_id = ?
            ORDER BY date DESC
            LIMIT ?
        ''', (employee_id, limit))
        return c.fetchall()


def get_attendance_records_for_year(employee_id, total_days=365):
    cutoff_date = (date.today() - timedelta(days=total_days - 1)).isoformat()
    with get_db() as conn:
        c = conn.cursor()
        c.execute('''
            SELECT date, check_in, check_out, video_path
            FROM attendance
            WHERE employee_id = ? AND date >= ?
            ORDER BY date DESC
        ''', (employee_id, cutoff_date))
        return [dict(row) for row in c.fetchall()]


def save_attendance_video(employee_id, file_storage):
    if not file_storage or file_storage.filename == '':
        return None

    filename = secure_filename(file_storage.filename)
    if not allowed_video_filename(filename):
        return None

    target_name = f"checkin_{employee_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
    target_path = os.path.join(VIDEO_DIR, target_name)
    file_storage.save(target_path)
    return target_name


def chunk_attendance_records(records, segment_days=30, total_days=365):
    segments = []
    today = date.today()
    cutoff = today - timedelta(days=total_days - 1)
    end_date = today

    while end_date >= cutoff:
        start_date = max(cutoff, end_date - timedelta(days=segment_days - 1))
        period_records = [record for record in records if start_date.isoformat() <= record['date'] <= end_date.isoformat()]
        segments.append({
            'label': f"{start_date.strftime('%b %d, %Y')} - {end_date.strftime('%b %d, %Y')}",
            'start_date': start_date,
            'end_date': end_date,
            'records': period_records
        })
        end_date = start_date - timedelta(days=1)

    return segments


def add_attendance_check_in(employee_id):
    today = date.today().isoformat()
    timestamp = datetime.now().strftime('%H:%M:%S')
    with get_db() as conn:
        c = conn.cursor()
        c.execute('''
            INSERT INTO attendance (employee_id, date, check_in)
            VALUES (?, ?, ?)
        ''', (employee_id, today, timestamp))
        conn.commit()
    return get_today_attendance(employee_id)


def add_attendance_check_out(employee_id):
    today = date.today().isoformat()
    timestamp = datetime.now().strftime('%H:%M:%S')
    with get_db() as conn:
        c = conn.cursor()
        c.execute('''
            UPDATE attendance
            SET check_out = ?
            WHERE employee_id = ? AND date = ?
        ''', (timestamp, employee_id, today))
        conn.commit()
    return get_today_attendance(employee_id)


init_db()


@app.before_request
def ensure_db_initialized():
    """Ensure database is initialized before every request"""
    global _db_initialized
    if not _db_initialized:
        try:
            init_db()
            _db_initialized = True
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            abort(500)


@app.route('/')
def home():
    if 'employee_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
@limiter.limit("5 per hour")
def register():
    if request.method == 'POST':
        employee_id = request.form.get('employee_id', '').strip()
        password = request.form.get('password', '').strip()
        name = request.form.get('name', '').strip()
        contact = request.form.get('contact', '').strip()
        gmail = request.form.get('gmail', '').strip()
        address = request.form.get('address', '').strip()
        postal_code = request.form.get('postal_code', '').strip()
        dob = request.form.get('dob', '').strip()

        # Input validation
        if not all([employee_id, password, name, gmail]):
            flash('Please fill in all required fields.', 'error')
            logger.warning(f"Registration attempt with missing fields from {get_remote_address()}")
            return render_template('register.html')
        
        if not is_valid_email(gmail):
            flash('Please enter a valid email address.', 'error')
            return render_template('register.html')
        
        is_strong, msg = is_strong_password(password)
        if not is_strong:
            flash(f'Password too weak: {msg}', 'error')
            return render_template('register.html')
        
        if len(employee_id) < 3:
            flash('Employee ID must be at least 3 characters.', 'error')
            return render_template('register.html')
        
        if len(name) < 2:
            flash('Name must be at least 2 characters.', 'error')
            return render_template('register.html')

        if get_employee_by_id(employee_id):
            flash('That employee ID is already registered.', 'error')
            logger.warning(f"Registration attempt with duplicate employee_id: {employee_id}")
            return render_template('register.html')

        password_hash = generate_password_hash(password)

        try:
            with get_db() as conn:
                c = conn.cursor()
                c.execute('''
                    INSERT INTO employees
                    (employee_id, password, name, contact, gmail,
                     address, postal_code, dob)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (employee_id, password_hash, name, contact,
                      gmail, address, postal_code, dob))
                conn.commit()
            logger.info(f"New employee registered: {employee_id}")
            flash('Registration successful. Please log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            logger.error(f"Registration error: {e}")
            flash('An error occurred during registration. Please try again.', 'error')
            return render_template('register.html')

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per hour")
def login():
    if request.method == 'POST':
        employee_id = request.form.get('employee_id', '').strip()
        password = request.form.get('password', '').strip()

        if not employee_id or not password:
            flash('Please enter employee ID and password.', 'error')
            return render_template('login.html')

        employee = get_employee_by_id(employee_id)
        if employee and check_password_hash(employee['password'], password):
            session['employee_id'] = employee['employee_id']
            session['employee_name'] = employee['name']
            session['is_admin'] = bool(employee['is_admin'])
            logger.info(f"Employee logged in: {employee_id}")
            return redirect(url_for('dashboard'))

        logger.warning(f"Failed login attempt for: {employee_id} from {get_remote_address()}")
        flash('Invalid employee ID or password.', 'error')
        return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/dashboard')
def dashboard():
    if 'employee_id' not in session:
        flash('Please log in to continue.', 'error')
        return redirect(url_for('login'))

    employee = get_employee_by_id(session['employee_id'])
    if not employee:
        session.clear()
        flash('Session expired. Please log in again.', 'error')
        return redirect(url_for('login'))

    today_attendance = get_today_attendance(session['employee_id'])
    history_records = get_attendance_records_for_year(session['employee_id'])
    attendance_segments = chunk_attendance_records(history_records)

    return render_template(
        'dashboard.html',
        employee=employee,
        today_attendance=today_attendance,
        attendance_segments=attendance_segments
    )


@app.route('/attendance/check-in', methods=['GET', 'POST'])
@limiter.limit("20 per hour")
def attendance_check_in():
    if 'employee_id' not in session:
        flash('Please log in to continue.', 'error')
        return redirect(url_for('login'))

    employee_id = session['employee_id']
    if request.method == 'GET':
        if get_today_attendance(employee_id):
            flash('You have already checked in today.', 'info')
            return redirect(url_for('dashboard'))

        verification_code = str(datetime.now().timestamp()).replace('.', '')[-6:]
        session['keyboard_code'] = verification_code
        logger.info(f"Check-in initiated for {employee_id}")
        return render_template('attendance_checkin.html', verification_code=verification_code)

    # POST
    attendance = get_today_attendance(employee_id)
    if attendance:
        flash('You have already checked in today.', 'info')
        return redirect(url_for('dashboard'))

    typed_code = request.form.get('verification_code', '').strip()
    expected_code = session.pop('keyboard_code', None)
    if typed_code != expected_code:
        flash('Keyboard verification failed. Please try again.', 'error')
        logger.warning(f"Verification code mismatch for {employee_id}")
        return redirect(url_for('attendance_check_in'))

    video_file = request.files.get('video_file')
    saved_filename = save_attendance_video(employee_id, video_file)
    if not saved_filename:
        flash('Video upload failed. Please upload a valid video file (webm, mp4, ogg).', 'error')
        logger.warning(f"Video upload failed for {employee_id}")
        return redirect(url_for('attendance_check_in'))

    try:
        video_path = f"checkin_videos/{saved_filename}"
        today = date.today().isoformat()
        timestamp = datetime.now().strftime('%H:%M:%S')
        with get_db() as conn:
            c = conn.cursor()
            c.execute('''
                INSERT INTO attendance (employee_id, date, check_in, video_path)
                VALUES (?, ?, ?, ?)
            ''', (employee_id, today, timestamp, video_path))
            conn.commit()

        cleanup_old_videos()
        logger.info(f"Check-in recorded for {employee_id} at {timestamp}")
        flash('✓ Check-in successful! Video verified.', 'success')
        return redirect(url_for('dashboard'))
    except Exception as e:
        logger.error(f"Check-in error for {employee_id}: {e}")
        flash('An error occurred during check-in. Please try again.', 'error')
        return redirect(url_for('attendance_check_in'))


@app.route('/attendance/check-out', methods=['POST'])
def attendance_check_out():
    if 'employee_id' not in session:
        flash('Please log in to continue.', 'error')
        return redirect(url_for('login'))

    employee_id = session['employee_id']
    try:
        attendance = get_today_attendance(employee_id)
        if not attendance:
            flash('Please check in before checking out.', 'error')
            logger.warning(f"Check-out attempted without check-in for {employee_id}")
        elif attendance['check_out']:
            flash('You have already checked out today.', 'info')
        else:
            add_attendance_check_out(employee_id)
            logger.info(f"Check-out recorded for {employee_id}")
            flash('✓ Check-out recorded successfully.', 'success')
    except Exception as e:
        logger.error(f"Check-out error for {employee_id}: {e}")
        flash('An error occurred during check-out. Please try again.', 'error')

    return redirect(url_for('dashboard'))


@app.route('/admin')
def admin_dashboard():
    if 'employee_id' not in session or not session.get('is_admin'):
        logger.warning(f"Unauthorized admin access attempt from {get_remote_address()}")
        abort(403)
    
    try:
        with get_db() as conn:
            c = conn.cursor()
            # Total employees
            c.execute('SELECT COUNT(*) as count FROM employees')
            total_employees = c.fetchone()['count']
            
            # Today's attendance
            today = date.today().isoformat()
            c.execute('''
                SELECT COUNT(DISTINCT employee_id) as checked_in,
                       SUM(CASE WHEN check_out IS NOT NULL THEN 1 ELSE 0 END) as checked_out
                FROM attendance
                WHERE date = ?
            ''', (today,))
            today_stats = c.fetchone()
            
            # Recent check-ins
            c.execute('''
                SELECT a.employee_id, e.name, a.date, a.check_in, a.check_out
                FROM attendance a
                JOIN employees e ON a.employee_id = e.employee_id
                ORDER BY a.date DESC, a.check_in DESC
                LIMIT 20
            ''')
            recent_records = [dict(row) for row in c.fetchall()]
            
        logger.info(f"Admin dashboard accessed by {session['employee_id']}")
        return render_template(
            'admin_dashboard.html',
            total_employees=total_employees,
            today_stats=today_stats,
            recent_records=recent_records
        )
    except Exception as e:
        logger.error(f"Admin dashboard error: {e}")
        flash('An error occurred loading the admin dashboard.', 'error')
        return redirect(url_for('dashboard'))


@app.errorhandler(403)
def forbidden(e):
    logger.warning(f"403 Forbidden error: {e}")
    return render_template('error.html', code=403, message='Access Denied'), 403


@app.errorhandler(404)
def not_found(e):
    logger.warning(f"404 Not Found error: {e}")
    return render_template('error.html', code=404, message='Page Not Found'), 404


@app.errorhandler(500)
def server_error(e):
    logger.error(f"500 Server error: {e}")
    return render_template('error.html', code=500, message='Internal Server Error'), 500


@app.route('/logout')
def logout():
    employee_id = session.get('employee_id', 'Unknown')
    session.clear()
    logger.info(f"Employee logged out: {employee_id}")
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('login'))


if __name__ == '__main__':
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    port = int(os.environ.get('PORT', 10000))
    app.run(debug=debug_mode, host='0.0.0.0', port=port)
