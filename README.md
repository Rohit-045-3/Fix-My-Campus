# FixMyCampus — Campus Issue Reporting System

A full-stack diploma project built with HTML, CSS, JavaScript, Bootstrap, Python Flask and MySQL.

## Features
- Student registration and login with hashed passwords
- 12 campus issue categories and photo attachments
- Priority levels and complaint ticket numbers
- Complaint status and update timeline
- Student dashboard and complaint history
- Staff dashboard for assigned/unassigned complaints
- Admin dashboard, complaint assignment, and user role management
- Searchable database-ready complaint records and dashboard statistics
- Responsive layout for desktop and mobile

## Requirements
- Python 3.10+
- MySQL Server or XAMPP MySQL
- A browser

## Setup on Windows
1. Extract the ZIP file.
2. Open PowerShell in the `FixMyCampus` folder.
3. Create and activate a virtual environment:
   ```powershell
   py -m venv venv
   .\venv\Scripts\Activate.ps1
   ```
4. Install packages:
   ```powershell
   pip install -r requirements.txt
   ```
5. Start MySQL from XAMPP Control Panel (or your MySQL service).
6. Import `schema.sql` in phpMyAdmin using the **Import** tab, or run it in MySQL Workbench.
7. Copy `.env.example` to `.env` and update database credentials. Set a long random `SECRET_KEY`.
8. Start the application:
   ```powershell
   python app.py
   ```
9. Open `http://127.0.0.1:5000`.

## Create the first admin
1. Register a normal account through the website.
2. Open phpMyAdmin, select the `fixmycampus` database, and open the SQL tab.
3. Replace `your-email@example.com` with the email used to register:
   ```sql
   UPDATE users SET role='admin' WHERE email='your-email@example.com';
   ```
4. Sign out and sign in again so the new role is loaded into the session.
5. To create staff accounts, register another account and update its role to `staff` in the same way.

## How to demonstrate
1. Register a student and submit a complaint with category, location, priority and optional photo.
2. Open the ticket detail page and show the status timeline.
3. Promote a second account to staff and demonstrate staff access.
4. Sign in as admin, assign complaints to staff, update statuses, and manage roles.
5. Show dashboard statistics and the complaint history.

## Important notes
- This is a starter academic project, not a production-ready campus deployment.
- Before public deployment, set `FLASK_DEBUG=false`, use a strong secret key, enable HTTPS, add CSRF protection and rate limiting, validate uploaded images more strictly, and configure secure session cookies.
- Do not upload real student personal information to a public demo.
- The default MySQL root account may have an empty password in a local XAMPP setup. Configure your own database credentials where needed.
