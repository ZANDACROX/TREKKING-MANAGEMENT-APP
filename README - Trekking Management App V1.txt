README - Trekking Management App V1
Overview:
The Trekking Management App is a web-based application built using Flask, SQLAlchemy, SQLite, and Bootstrap 5 to manage trekking expeditions, staff verifications, and user reservations across three roles: Admin, Trek Staff, and Users (Trekkers).  

Prerequisites:
Python 3.x installed on your system.
pip (Python package manager).

Installation & Running Instructions:

1. Navigate to the Project Root FolderOpen your terminal or command prompt and ensure you are in the main project directory containing app.py and models.py.  


2. Create and Activate a Virtual Environment (Recommended)
Bash
python -m venv venv

# On Windows:
venv\Scripts\activate

# On macOS / Linux:
source venv/bin/activate
3. Install Required Dependencies
Install the required Flask framework packages:

Bash
pip install Flask Flask-SQLAlchemy Flask-Login Werkzeug
4. Run the Application
Start the Flask development server by executing app.py:

Bash
python app.py
(Note: The application is configured to automatically initialize the SQLite database trekking.db and create a default superuser admin account on startup).  


5. Access the App in Your Browser
Open your preferred web browser and go to:


http://127.0.0.1:5000/


Default Admin Credentials
Username: admin
Password: adminpassword

