# KrishiBondhu Setup Instructions

## Prerequisites
- Python 3.x installed
- Oracle Database (11g or later) OR Oracle Express Edition
- Oracle Instant Client (optional, if Oracle Client is not installed system-wide)

## Step 1: Configure Database Credentials

1. Edit the `.env` file in the project root:
   ```
   # Oracle Database Configuration
   INSTANT_CLIENT_PATH=/path/to/oracle/instantclient  # Leave empty if Oracle Client is installed system-wide
   DB_USER=your_username
   DB_PASSWORD=your_password
   DB_DSN=localhost:1521/ORCL  # Adjust based on your Oracle setup
   ```

2. Update with your actual Oracle database credentials.

## Step 2: Create Database Tables and Users

### Option A: Using SQL Script (Recommended)

1. Connect to your Oracle database using SQL*Plus or any SQL client:
   ```bash
   sqlplus username/password@TNS_NAME
   ```

2. Run the sample users SQL script:
   ```sql
   @sample_users.sql
   ```

### Option B: Manual SQL Execution

Execute the SQL commands from `sample_users.sql` directly in your Oracle database.

## Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 4: Run the Application

```bash
python3 app.py
```

The application will start on: **http://127.0.0.1:5000**

## Test User Credentials

### Login with Username:
- **Username:** `farmer1` → **Password:** `password123`
- **Username:** `farmer2` → **Password:** `password123`
- **Username:** `agent1` → **Password:** `password123`
- **Username:** `agent2` → **Password:** `password123`
- **Username:** `advisor1` → **Password:** `password123`
- **Username:** `admin` → **Password:** `password123`

### Login with Phone Number:
- **Phone:** `01911234567` → **Password:** `password123`
- **Phone:** `01912345678` → **Password:** `password123`
- **Phone:** `01721234567` → **Password:** `password123`
- **Phone:** `01722345678` → **Password:** `password123`
- **Phone:** `01831234567` → **Password:** `password123`
- **Phone:** `01941234567` → **Password:** `password123`

## User Roles

- **Farmer** - Regular farmer dashboard
- **Agent** - Agent dashboard with inventory and loan management
- **Advisor** - Agricultural advisor dashboard
- **Admin** - Administrator dashboard

## Troubleshooting

### Database Connection Error
- Verify Oracle database is running
- Check `.env` file credentials
- Ensure Instant Client path is correct (if provided)

### Module Not Found
- Run `pip install -r requirements.txt`
- Verify Python 3 is being used (not Python 2)

### Port Already in Use
- Change the port in `app.py` (line 12): `app.run(debug=True, port=5001)`

## Database Schema

The application expects the following `PERSON` table structure:

```sql
CREATE TABLE PERSON (
    person_id NUMBER PRIMARY KEY,
    first_name VARCHAR2(100) NOT NULL,
    last_name VARCHAR2(100) NOT NULL,
    username VARCHAR2(100) UNIQUE,
    password VARCHAR2(100),
    login_phone VARCHAR2(20) UNIQUE,
    role VARCHAR2(50) NOT NULL,
    -- Add other fields as needed
);
```

**Note:** Make sure this table exists in your Oracle database before running the application.
