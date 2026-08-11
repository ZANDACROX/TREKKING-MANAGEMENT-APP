import os
from datetime import datetime
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
                username='admin', email='admin@trekking.com',
                password=hashed_password, role='admin', status='active'
            )
            db.session.add(default_admin)
            db.session.commit()

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

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html')

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin': return redirect(url_for('login'))
    total_treks = Trek.query.count()
    total_users = User.query.filter_by(role='user').count()
    total_staff = User.query.filter_by(role='staff').count()
    total_bookings = Booking.query.count()
    return render_template('admin_dashboard.html', total_treks=total_treks, total_users=total_users, 
                           total_staff=total_staff, total_bookings=total_bookings)

@app.route('/admin/treks', methods=['GET', 'POST'])
@login_required
def admin_treks():
    if current_user.role != 'admin': return redirect(url_for('login'))
    if request.method == 'POST':
        new_trek = Trek(
            name=request.form.get('name'), location=request.form.get('location'),
            difficulty=request.form.get('difficulty'), duration=request.form.get('duration'),
            available_slots=request.form.get('available_slots'), start_date=request.form.get('start_date'),
            end_date=request.form.get('end_date')
        )
        db.session.add(new_trek)
        db.session.commit()
        flash('New trek created!', 'success')
        return redirect(url_for('admin_treks'))
    all_treks = Trek.query.all()
    approved_staff = User.query.filter_by(role='staff', status='approved').all()
    return render_template('admin_treks.html', treks=all_treks, staff_list=approved_staff)

@app.route('/admin/edit_trek/<int:trek_id>', methods=['GET', 'POST'])
@login_required
def admin_edit_trek(trek_id):
    if current_user.role != 'admin': return redirect(url_for('login'))
    trek = Trek.query.get(trek_id)
    if not trek: return redirect(url_for('admin_treks'))
    
    if request.method == 'POST':
        trek.name = request.form.get('name')
        trek.location = request.form.get('location')
        trek.difficulty = request.form.get('difficulty')
        trek.duration = request.form.get('duration')
        trek.available_slots = request.form.get('available_slots')
        trek.start_date = request.form.get('start_date')
        trek.end_date = request.form.get('end_date')
        db.session.commit()
        flash('Trek updated successfully!', 'success')
        return redirect(url_for('admin_treks'))
        
    return render_template('admin_edit_trek.html', trek=trek)

@app.route('/admin/delete_trek/<int:trek_id>', methods=['POST'])
@login_required
def admin_delete_trek(trek_id):
    if current_user.role != 'admin': return redirect(url_for('login'))
    trek = Trek.query.get(trek_id)
    if trek:
        db.session.delete(trek)
        db.session.commit()
        flash('Trek deleted successfully!', 'success')
    return redirect(url_for('admin_treks'))

@app.route('/admin/search', methods=['GET'])
@login_required
def admin_search():
    if current_user.role != 'admin': return redirect(url_for('login'))
    query = request.args.get('q', '')
    search_type = request.args.get('type', 'trek')
    results = []
    
    if query:
        if search_type == 'trek':
            results = Trek.query.filter(Trek.name.ilike(f'%{query}%')).all()
        elif search_type == 'staff':
            results = User.query.filter(User.role == 'staff', User.username.ilike(f'%{query}%')).all()
        elif search_type == 'user':
            results = User.query.filter(User.role == 'user', User.username.ilike(f'%{query}%')).all()
            
    return render_template('admin_search.html', results=results, query=query, search_type=search_type)

@app.route('/admin/staff', methods=['GET', 'POST'])
@login_required
def admin_staff():
    if current_user.role != 'admin': return redirect(url_for('login'))
    if request.method == 'POST':
        user_to_modify = User.query.get(request.form.get('user_id'))
        action = request.form.get('action')
        if user_to_modify and user_to_modify.role == 'staff':
            if action == 'approve': user_to_modify.status = 'approved'
            elif action == 'blacklist': user_to_modify.status = 'blacklisted'
            elif action == 'activate': user_to_modify.status = 'approved'
            db.session.commit()
        return redirect(url_for('admin_staff'))
    staff_members = User.query.filter_by(role='staff').all()
    return render_template('admin_staff.html', staff=staff_members)

@app.route('/admin/users', methods=['GET', 'POST'])
@login_required
def admin_users():
    if current_user.role != 'admin': return redirect(url_for('login'))
    if request.method == 'POST':
        user_to_modify = User.query.get(request.form.get('user_id'))
        action = request.form.get('action')
        if user_to_modify and user_to_modify.role == 'user':
            if action == 'blacklist': user_to_modify.status = 'blacklisted'
            elif action == 'activate': user_to_modify.status = 'active'
            db.session.commit()
        return redirect(url_for('admin_users'))
    regular_users = User.query.filter_by(role='user').all()
    return render_template('admin_users.html', users=regular_users)

@app.route('/admin/assign_staff', methods=['POST'])
@login_required
def assign_staff():
    if current_user.role != 'admin': return redirect(url_for('login'))
    trek = Trek.query.get(request.form.get('trek_id'))
    if trek:
        trek.assigned_staff_id = request.form.get('staff_id')
        db.session.commit()
        flash('Staff assigned successfully!', 'success')
    return redirect(url_for('admin_treks'))

@app.route('/admin/bookings')
@login_required
def admin_bookings():
    if current_user.role != 'admin': return redirect(url_for('login'))
    all_bookings = Booking.query.all()
    return render_template('admin_bookings.html', bookings=all_bookings)

@app.route('/staff/dashboard')
@login_required
def staff_dashboard():
    if current_user.role != 'staff': return redirect(url_for('login'))
    assigned_treks = Trek.query.filter_by(assigned_staff_id=current_user.id).all()
    trek_ids = [t.id for t in assigned_treks]
    total_participants = Booking.query.filter(Booking.trek_id.in_(trek_ids)).count() if trek_ids else 0
    return render_template('staff_dashboard.html', total_treks=len(assigned_treks), total_participants=total_participants)

@app.route('/staff/treks')
@login_required
def staff_treks():
    if current_user.role != 'staff': return redirect(url_for('login'))
    assigned_treks = Trek.query.filter_by(assigned_staff_id=current_user.id).all()
    return render_template('staff_treks.html', treks=assigned_treks)

@app.route('/staff/manage_trek/<int:trek_id>', methods=['POST'])
@login_required
def staff_manage_trek(trek_id):
    if current_user.role != 'staff': return redirect(url_for('login'))
    trek = Trek.query.get(trek_id)
    if trek and trek.assigned_staff_id == current_user.id:
        if request.form.get('available_slots'): trek.available_slots = int(request.form.get('available_slots'))
        if request.form.get('status'): trek.status = request.form.get('status')
        db.session.commit()
        flash('Trek updated successfully!', 'success')
    return redirect(url_for('staff_treks'))

@app.route('/staff/participants')
@login_required
def staff_participants():
    if current_user.role != 'staff': return redirect(url_for('login'))
    assigned_treks = Trek.query.filter_by(assigned_staff_id=current_user.id).all()
    trek_ids = [t.id for t in assigned_treks]
    bookings = Booking.query.filter(Booking.trek_id.in_(trek_ids)).all() if trek_ids else []
    return render_template('staff_participants.html', bookings=bookings)

@app.route('/user/dashboard', methods=['GET'])
@login_required
def user_dashboard():
    if current_user.role != 'user': return redirect(url_for('login'))
    search_location = request.args.get('location', '')
    search_difficulty = request.args.get('difficulty', '')
    query = Trek.query.filter_by(status='Open')
    
    if search_location: query = query.filter(Trek.location.ilike(f"%{search_location}%"))
    if search_difficulty: query = query.filter_by(difficulty=search_difficulty)
        
    return render_template('user_dashboard.html', treks=query.all(), location=search_location, difficulty=search_difficulty)

@app.route('/user/book/<int:trek_id>', methods=['POST'])
@login_required
def book_trek(trek_id):
    if current_user.role != 'user': return redirect(url_for('login'))
    trek = Trek.query.get(trek_id)
    if not trek or trek.status != 'Open' or trek.available_slots <= 0:
        flash('Trek unavailable.', 'danger')
        return redirect(url_for('user_dashboard'))
        
    if Booking.query.filter_by(user_id=current_user.id, trek_id=trek.id).first():
        flash('Already booked!', 'warning')
        return redirect(url_for('user_dashboard'))
        
    new_booking = Booking(user_id=current_user.id, trek_id=trek.id, booking_date=datetime.now().strftime('%Y-%m-%d'), status='Booked')
    trek.available_slots -= 1 
    db.session.add(new_booking)
    db.session.commit()
    flash(f'Booked {trek.name}!', 'success')
    return redirect(url_for('user_bookings'))

@app.route('/user/unbook/<int:booking_id>', methods=['POST'])
@login_required
def unbook_trek(booking_id):
    if current_user.role != 'user': return redirect(url_for('login'))
    booking = Booking.query.get(booking_id)
    if booking and booking.user_id == current_user.id and booking.status == 'Booked':
        days_until = (datetime.strptime(booking.trek.start_date, '%Y-%m-%d') - datetime.now()).days
        if days_until >= 10:
            booking.status = 'Cancelled'
            booking.trek.available_slots += 1 
            db.session.commit()
            flash('Booking cancelled.', 'success')
        else:
            flash(f'Cannot cancel. Trek starts in {days_until} days.', 'danger')
    return redirect(url_for('user_bookings'))

@app.route('/user/bookings')
@login_required
def user_bookings():
    if current_user.role != 'user': return redirect(url_for('login'))
    active_bookings = Booking.query.filter_by(user_id=current_user.id, status='Booked').all()
    return render_template('user_bookings.html', bookings=active_bookings)

@app.route('/user/history')
@login_required
def user_history():
    if current_user.role != 'user': return redirect(url_for('login'))
    all_bookings = Booking.query.filter_by(user_id=current_user.id).all()
    return render_template('user_history.html', bookings=all_bookings)

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)