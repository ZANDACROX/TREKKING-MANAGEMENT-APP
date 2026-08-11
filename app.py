import os
from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from models import db, User, StaffProfile, Trek, Booking

app = Flask(__name__)
app.config['SECRET_KEY'] = 'trekking_secret_key_2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///trekking.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def init_db():
    with app.app_context():
        db.create_all()
        admin = User.query.filter_by(role='admin').first()
        if not admin:
            hashed_password = generate_password_hash('adminpassword')
            default_admin = User(
                username='admin',
                email='admin@trekking.com',
                password=hashed_password,
                role='admin',
                status='active'
            )
            db.session.add(default_admin)
            db.session.commit()
            print("Database initialized! Default Admin created.")

@app.route('/', methods=['GET'])
def home():
    if current_user.is_authenticated:
        if current_user.role == 'admin': return redirect(url_for('admin_dashboard'))
        if current_user.role == 'staff': return redirect(url_for('staff_dashboard'))
        if current_user.role == 'user': return redirect(url_for('user_dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            if user.role == 'staff' and user.status == 'pending':
                flash('Your staff account is pending Admin approval.', 'warning')
                return redirect(url_for('login'))
            
            if user.status == 'blacklisted':
                flash('Your account has been deactivated.', 'danger')
                return redirect(url_for('login'))

            login_user(user)
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password.', 'danger')
            
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')
        phone = request.form.get('phone')

        if User.query.filter_by(username=username).first() or User.query.filter_by(email=email).first():
            flash('Username or Email already exists!', 'danger')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)
        
        account_status = 'pending' if role == 'staff' else 'active'

        new_user = User(username=username, email=email, password=hashed_password, role=role, status=account_status)
        db.session.add(new_user)
        db.session.commit()

        if role == 'staff':
            new_profile = StaffProfile(user_id=new_user.id, phone=phone)
            db.session.add(new_profile)
            db.session.commit()

        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/admin/dashboard')
@login_required
def admin_dashboard(): return "<h1>Admin Dashboard (Coming in Milestone 3)</h1><a href='/logout'>Logout</a>"

@app.route('/staff/dashboard')
@login_required
def staff_dashboard(): return "<h1>Staff Dashboard (Coming in Milestone 4)</h1><a href='/logout'>Logout</a>"

@app.route('/user/dashboard')
@login_required
def user_dashboard(): return "<h1>User Dashboard (Coming in Milestone 5)</h1><a href='/logout'>Logout</a>"

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)