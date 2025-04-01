# Issue Tracking System

A comprehensive issue tracking system built with Flask that supports multiple user roles and real-time updates.

## Features

- Role-based access control (Admin, Team Lead, Team Member, MD)
- Real-time issue updates using WebSocket
- Interactive dashboards for each role
- Issue tracking and management
- Team performance monitoring
- Statistical reports and PDF generation

## Prerequisites

- Python 3.8 or higher
- MySQL Server
- Virtual environment (recommended)

## Setup Instructions

1. Create and activate a virtual environment:
```bash
python -m venv venv
# On Windows
venv\Scripts\activate
# On Unix or MacOS
source venv/bin/activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create MySQL database:
```sql
CREATE DATABASE issue_tracking;
```

4. Configure environment variables:
- Copy `.env.example` to `.env`
- Update the database credentials in `.env`

5. Initialize the database:
```bash
flask db init
flask db migrate
flask db upgrade
```

6. Create an admin user:
```bash
flask create-admin
```

## Running the Application

1. Start the Flask application:
```bash
python app.py
```

2. Access the application at `http://localhost:5000`

## User Roles

- **Admin**: Full system access, user and team management
- **Team Lead**: Issue management for their team
- **Team Member**: View and update issues assigned to their team
- **MD**: View overall statistics and team performance

## Security Notes

- Keep your `.env` file secure and never commit it to version control
- Change the default secret key in production
- Use strong passwords for all user accounts 