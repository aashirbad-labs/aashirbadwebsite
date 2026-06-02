# 🏢 Employee Attendance System - Improved Version

A secure, modern Flask-based employee attendance tracking system with video verification, two-factor authentication, and comprehensive logging.

## ✨ Recent Improvements (v2.0)

### 🔒 Security Enhancements
- **CSRF Protection** - All forms protected with Flask-WTF
- **Rate Limiting** - Brute force protection on login (10/hour) and registration (5/hour)
- **Strong Password Requirements** - Minimum 8 characters with uppercase, lowercase, and digits
- **Email Validation** - Proper email format verification
- **Input Validation** - All user inputs validated and sanitized
- **Environment Variables** - Sensitive configs moved to `.env` file
- **Debug Mode Disabled** - Production-safe configuration

### ⚡ Performance Improvements
- **Database Indexes** - Added indexes on `employee_id` and `date` columns for faster queries
- **Foreign Keys** - Proper relationships between tables
- **Connection Pooling** - Better resource management
- **Schema Migrations** - Automatic table schema updates

### 📊 Admin Dashboard
- View total employees and daily statistics
- Real-time attendance monitoring
- Recent records overview
- Admin-only access control

### 📝 Comprehensive Logging
- Activity logging for all operations
- Error tracking and debugging
- Failed login attempts monitored
- Session management tracked
- Logs stored in `app.log`

### 🎨 Enhanced UI/UX
- Improved form validation with user-friendly messages
- Better visual feedback and status indicators
- Emoji icons for better UX
- Responsive design with mobile support
- Animated success/error messages
- Enhanced dashboard with admin link
- Better accessibility and semantic HTML

### 🛡️ Error Handling
- Custom error pages (403, 404, 500)
- Graceful error recovery
- User-friendly error messages
- Detailed logging for debugging

## 🚀 Quick Start

### Prerequisites
- Python 3.7+
- pip (Python package manager)

### Installation

1. **Clone the project from GitHub**
```bash
git clone https://github.com/YOUR_USERNAME/website.git
cd website
```

2. **Create .env file** (copy from .env.example)
```bash
# On Windows
copy .env.example .env

# On Mac/Linux
cp .env.example .env
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Initialize the database** (first time only)
```bash
python init_db.py
```

5. **Run the application**
```bash
python app.py
```

6. **Access the app**
- Open browser: `http://localhost:5000`
- Default port: 5000

> **Note:** If you get 404 errors, make sure you've run `python init_db.py` to initialize the database.

## 📋 Features

### Employee Features
- ✅ **Registration** - Create account with secure password
- ✅ **Login** - Rate-limited authentication with session management
- ✅ **Check-in/Check-out** - Video-verified attendance with 2-step verification
- ✅ **Attendance History** - View last 12 months of records
- ✅ **Profile Management** - View and manage employee information
- ✅ **Video Records** - Access to check-in verification videos

### Admin Features
- 📊 **Dashboard** - Overview of employees and attendance
- 📈 **Statistics** - Real-time attendance metrics
- 📋 **Records** - View all attendance records
- 🔍 **Monitoring** - Employee activity tracking

## 🏗️ Project Structure

```
website/
├── app.py                      # Main Flask application
├── requirements.txt            # Python dependencies
├── .env                        # Environment variables (local)
├── .env.example               # Environment template
├── app.log                     # Activity logs
├── employees.db               # SQLite database
├── static/
│   ├── style.css             # Global styles
│   └── checkin_videos/       # Stored verification videos
└── templates/
    ├── login.html            # Login page
    ├── register.html         # Registration page
    ├── dashboard.html        # Employee dashboard
    ├── attendance_checkin.html # Video verification
    ├── admin_dashboard.html  # Admin panel
    └── error.html            # Error pages
```

## 🔧 Configuration

### Environment Variables (.env)

```env
FLASK_ENV=production              # Set to 'development' for debug mode
FLASK_SECRET_KEY=your_secret_key  # Change this to a random string!
FLASK_DEBUG=False                 # Never enable in production
DB_PATH=employees.db              # Database file location
VIDEO_MAX_AGE_DAYS=30            # Delete videos older than 30 days
```

## 📚 API Endpoints

### Authentication
- `POST /register` - Register new employee
- `POST /login` - Employee login
- `GET /logout` - Logout

### Attendance
- `GET /dashboard` - View employee dashboard
- `GET /attendance/check-in` - Start check-in process
- `POST /attendance/check-in` - Submit check-in with video
- `POST /attendance/check-out` - Record check-out

### Admin
- `GET /admin` - Admin dashboard (admin only)

## 🔐 Security Features

| Feature | Description |
|---------|-------------|
| CSRF Protection | Form token validation |
| Rate Limiting | 10 login attempts/hour, 5 registration/hour |
| Password Policy | Min 8 chars, uppercase, lowercase, digits |
| Email Validation | RFC-compliant email checking |
| Input Sanitization | All inputs validated and escaped |
| Video Storage | Time-limited storage (30 days default) |
| Session Management | Secure session handling with timeout |
| Admin Authorization | Role-based access control |
| Logging & Audit | All activities logged for compliance |

## 📊 Database Schema

### Employees Table
```sql
CREATE TABLE employees (
    id INTEGER PRIMARY KEY,
    employee_id TEXT UNIQUE,
    password TEXT (hashed with bcrypt),
    name TEXT,
    contact TEXT,
    gmail TEXT,
    address TEXT,
    postal_code TEXT,
    dob TEXT,
    is_admin INTEGER (0/1),
    created_at TIMESTAMP
);
```

### Attendance Table
```sql
CREATE TABLE attendance (
    id INTEGER PRIMARY KEY,
    employee_id TEXT,
    date TEXT (YYYY-MM-DD),
    check_in TEXT (HH:MM:SS),
    check_out TEXT (HH:MM:SS),
    video_path TEXT,
    UNIQUE(employee_id, date),
    FOREIGN KEY(employee_id) REFERENCES employees(employee_id)
);
```

## 📹 Video Check-in Process

1. **Permission**: Employee grants camera access
2. **Recording**: Captures video of keyboard and environment
3. **Verification**: Employee types a random 6-digit code
4. **Upload**: Video + code submitted for verification
5. **Storage**: Video stored with automatic cleanup after 30 days

## 🚢 Deployment

### For Production Use

1. **Use a WSGI Server** (not Flask development server)
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

2. **Set environment to production**
```bash
set FLASK_ENV=production
set FLASK_DEBUG=False
```

3. **Use HTTPS** - Install SSL certificate
4. **Database** - Use PostgreSQL for production (not SQLite)
5. **Storage** - Use cloud storage (S3) for videos

## 📝 Logging

All activities are logged to `app.log`:

```
2026-06-02 23:48:05,612 - __main__ - INFO - Added is_admin column to employees table
2026-06-02 23:48:05,650 - __main__ - INFO - Created database indexes
2026-06-02 23:48:39,692 - werkzeug - INFO - Running on http://127.0.0.1:5000
```

## 🐛 Troubleshooting

### Camera Access Issues
- Check browser permissions for camera
- Try Chrome, Firefox, or Edge browsers
- Allow HTTPS access if required

### Database Errors
- Delete `employees.db` and restart (will recreate)
- Check file permissions
- Ensure SQLite is installed

### Port Already in Use
```bash
# Change port in app.py or use environment variable
```

## 🔄 Future Improvements

- [ ] Mobile app with biometric verification
- [ ] Geolocation-based check-in
- [ ] Holiday and leave management
- [ ] Email notifications
- [ ] Export reports (PDF/Excel)
- [ ] Dark mode toggle
- [ ] Analytics dashboard
- [ ] Multi-location support

## 📄 License

Internal Use Only - Company Confidential

## 👥 Support

For issues or improvements, contact your system administrator.

---

**Version**: 2.0  
**Last Updated**: June 2, 2026  
**Status**: Production Ready ✅
