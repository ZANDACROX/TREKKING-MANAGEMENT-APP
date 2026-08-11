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
def admin_dashboard():
    if current_user.role != 'admin':
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('login'))
    
    total_treks = Trek.query.count()
    total_users = User.query.filter_by(role='user').count()
    total_staff = User.query.filter_by(role='staff').count()
    total_bookings = Booking.query.count()
    
    return render_template('admin_dashboard.html', 
                           total_treks=total_treks, 
                           total_users=total_users, 
                           total_staff=total_staff, 
                           total_bookings=total_bookings)

@app.route('/admin/treks', methods=['GET', 'POST'])
@login_required
def admin_treks():
    if current_user.role != 'admin':
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        name = request.form.get('name')
        location = request.form.get('location')
        difficulty = request.form.get('difficulty')
        duration = request.form.get('duration')
        slots = request.form.get('available_slots')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        
        new_trek = Trek(name=name, location=location, difficulty=difficulty, 
                        duration=duration, available_slots=slots, 
                        start_date=start_date, end_date=end_date)
        db.session.add(new_trek)
        db.session.commit()
        flash('New trek successfully created!', 'success')
        return redirect(url_for('admin_treks'))
        
    all_treks = Trek.query.all()
    approved_staff = User.query.filter_by(role='staff', status='approved').all()
    return render_template('admin_treks.html', treks=all_treks, staff_list=approved_staff)

@app.route('/admin/users', methods=['GET', 'POST'])
@login_required
def admin_users():
    if current_user.role != 'admin':
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        target_user_id = request.form.get('user_id')
        action = request.form.get('action')
        user_to_modify = User.query.get(target_user_id)
        
        if user_to_modify:
            if action == 'approve':
                user_to_modify.status = 'approved'
                flash(f'Staff {user_to_modify.username} approved!', 'success')
            elif action == 'blacklist':
                user_to_modify.status = 'blacklisted'
                flash(f'User {user_to_modify.username} blacklisted!', 'danger')
            elif action == 'activate':
                user_to_modify.status = 'active'
                flash(f'User {user_to_modify.username} reactivated!', 'success')
            db.session.commit()
            
        return redirect(url_for('admin_users'))

    staff_members = User.query.filter_by(role='staff').all()
    regular_users = User.query.filter_by(role='user').all()
    return render_template('admin_users.html', staff=staff_members, users=regular_users)

@app.route('/admin/assign_staff', methods=['POST'])
@login_required
def assign_staff():
    if current_user.role != 'admin':
        return redirect(url_for('login'))
        
    trek_id = request.form.get('trek_id')
    staff_id = request.form.get('staff_id')
    
    trek = Trek.query.get(trek_id)
    if trek:
        trek.assigned_staff_id = staff_id
        db.session.commit()
        flash('Staff assigned to trek successfully!', 'success')
        
    return redirect(url_for('admin_treks'))

@app.route('/staff/dashboard')
@login_required
def staff_dashboard():
    if current_user.role != 'staff':
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('login'))
    
    assigned_treks = Trek.query.filter_by(assigned_staff_id=current_user.id).all()
    
    return render_template('staff_dashboard.html', treks=assigned_treks)

@app.route('/staff/manage_trek/<int:trek_id>', methods=['GET', 'POST'])
@login_required
def staff_manage_trek(trek_id):
    if current_user.role != 'staff':
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('login'))
        
    trek = Trek.query.get(trek_id)
    
    if not trek or trek.assigned_staff_id != current_user.id:
        flash('You are not authorized to manage this trek.', 'danger')
        return redirect(url_for('staff_dashboard'))
        
    if request.method == 'POST':
        new_slots = request.form.get('available_slots')
        new_status = request.form.get('status')
        
        if new_slots:
            trek.available_slots = int(new_slots)
        if new_status:
            trek.status = new_status
            
        db.session.commit()
        flash('Trek details updated successfully!', 'success')
        return redirect(url_for('staff_manage_trek', trek_id=trek.id))
        
    trek_bookings = Booking.query.filter_by(trek_id=trek.id).all()
    
    return render_template('staff_manage_trek.html', trek=trek, bookings=trek_bookings)

@app.route('/user/dashboard')
@login_required
def user_dashboard(): return "<h1>User Dashboard (Coming in Milestone 5)</h1><a href='/logout'>Logout</a>"

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)