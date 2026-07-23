# AutoCare Pro

AutoCare Pro is a Flask-based vehicle maintenance and service tracking web application created for the CSCI 4950 STEM Project Seminar.

## Project Purpose

Vehicle owners often forget routine services, lose maintenance records, and have no single place to monitor repair costs or upcoming maintenance. AutoCare Pro provides one organized dashboard for vehicles, maintenance history, service reminders, and cost tracking.

## Final Features

- User registration and secure password hashing
- User login and logout
- Add, edit, and delete vehicles
- Add, edit, and delete maintenance records
- Maintenance history for each vehicle
- Filter maintenance history by service type and date range
- Maintenance cost tracking
- Current-year maintenance cost analytics
- Automatic vehicle mileage updates from newer maintenance records
- Date- and mileage-based maintenance reminders
- Due / Upcoming reminder status
- Dashboard analytics for vehicles, mileage, records, costs, and reminders
- SQLite relational database
- Responsive HTML/CSS interface
- JSON vehicle API endpoint

## Architecture

Browser / Frontend (HTML + CSS + JavaScript)
        |
        | HTTP requests / responses
        v
Python Flask Backend (app.py)
        |
        | SQL queries
        v
SQLite Database (autocare.db)

### Main Database Tables

- `users`
- `vehicles`
- `maintenance_records`
- `reminders`

Relationships:

- One user can own many vehicles.
- One vehicle can have many maintenance records.
- One vehicle can have many maintenance reminders.

## Technologies

- Python
- Flask
- SQLite
- HTML
- CSS
- JavaScript
- Werkzeug password hashing

## Local Setup Instructions

### 1. Clone or download the project

If using Git:

```bash
git clone https://github.com/Wifi2k/AutoCare-Pro.git
cd AutoCare-Pro
```

Or download the ZIP and extract it.

### 2. Install dependencies

Windows:

```powershell
py -m pip install -r requirements.txt
```

### 3. Run the application

```powershell
py app.py
```

### 4. Open the website

Open a browser and go to:

```text
http://127.0.0.1:5000
```

## Suggested Final Demonstration

1. Register or log in.
2. Add a vehicle.
3. Edit the vehicle.
4. Add a maintenance record.
5. Show the dashboard analytics update.
6. Edit a maintenance record.
7. Filter maintenance history.
8. Create a maintenance reminder.
9. Demonstrate Due / Upcoming status.
10. Delete a test maintenance record or reminder.
11. Briefly show the Flask routes and SQLite database code in `app.py`.

## SDLC Progression

### Requirements
Defined the target problem, user persona, functional requirements, and technical constraints.

### Design
Created architecture diagrams, database entities, wireframes, and user-flow diagrams.

### Prototype
Implemented a vertical slice where the user entered vehicle data, Flask processed it, SQLite stored it, and the dashboard updated.

### Final Build
Expanded the prototype with complete vehicle management, maintenance CRUD, reminders, filtering, and analytics.

## Security Notes

Passwords are not stored as plain text. Werkzeug password hashing is used before user credentials are written to the database.

The included Flask development server is intended for local demonstration and course evaluation.
