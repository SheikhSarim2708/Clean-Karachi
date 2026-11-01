# CleanKarachi: Waste Reporting and Management System

A web-based system where citizens report waste-related problems, staff resolve
them, and administrators oversee operations and reports.

## Technology Stack
- Backend: Python, Flask, REST APIs
- Database: MySQL
- Frontend: HTML, CSS, Bootstrap, JavaScript
- Architecture: three layers (presentation, business logic, data)
- Access control: role-based (Citizen, Staff, Administrator)

## Project Structure
```
CleanKarachi/
├── Backend/     Flask application and REST APIs
└── Frontend/    User interface
```

## Backend Setup

### 1. Prerequisites
- Python 3.10 or newer
- MySQL Server and MySQL Workbench

### 2. Create the database
Open MySQL Workbench and run the file `Backend/schema.sql`. It creates the
`cleankarachi` database, all tables, and the starting data (roles, categories, areas).

### 3. Create the virtual environment and install dependencies
```
cd Backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Configure the application
Copy `config.example.py` and rename the copy to `config.py`. Open it and set your
MySQL password and a secret key.

### 5. Create the admin and staff users
```
python create_users.py
```
Default demo accounts (change these passwords for real use):

| Role | Email | Password |
|---|---|---|
| Admin | admin@cleankarachi.com | admin123 |
| Staff | staff1@cleankarachi.com | staff123 |
| Staff | staff2@cleankarachi.com | staff123 |

Citizens register through `POST /api/register`.

### 6. Run the server
```
python app.py
```
The API runs at `http://127.0.0.1:5000`.

## API Documentation
See `Backend/API_DOCUMENTATION.md`.

## Main Features
- Citizen: register, submit complaints with photos, track status timeline
- Staff: view assigned complaints, update status, upload resolution proof
- Admin: manage complaints, assign and reassign staff, manage users, categories
  and areas, view reports, export CSV

## Security
Password hashing, session authentication, role-based access control, input
validation, parameterized SQL queries, and secure file upload (type check,
size limit, random file names).