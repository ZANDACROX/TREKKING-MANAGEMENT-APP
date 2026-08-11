import os
from flask import Flask
from models import db, User

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///trekking.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

def init_db():
    with app.app_context():
        db.create_all()
        admin = User.query.filter_by(role='admin').first()
        if not admin:
            default_admin = User(
                username='admin',
                email='admin@trekking.com',
                password='adminpassword',
                role='admin',
                status='active'
            )
            db.session.add(default_admin)
            db.session.commit()

@app.route('/')
def home():
    return "Milestone 1 Complete: Database initialized with default admin."

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)