import sqlite3
import os

def init_database(db_path="krishibondhu.db"):
    """Initialize SQLite database with required tables"""
    
    # Remove existing database if you want a fresh start
    # if os.path.exists(db_path):
    #     os.remove(db_path)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON")
    
    # Create PERSON table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS PERSON (
            person_id INTEGER PRIMARY KEY,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            username TEXT UNIQUE,
            password TEXT,
            login_phone TEXT UNIQUE,
            role TEXT NOT NULL CHECK(role IN ('FARMER', 'AGENT', 'ADVISOR', 'ADMIN')),
            last_login TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create PHONE table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS PHONE (
            phone_id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id INTEGER NOT NULL,
            phone_number TEXT UNIQUE,
            phone_type TEXT,
            is_primary TEXT,
            FOREIGN KEY(person_id) REFERENCES PERSON(person_id) ON DELETE CASCADE
        )
    """)
    
    # Create FARMER table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS FARMER (
            farmer_code INTEGER PRIMARY KEY,
            person_id INTEGER UNIQUE,
            agent_code INTEGER,
            center_code INTEGER,
            land_area REAL,
            registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(person_id) REFERENCES PERSON(person_id) ON DELETE CASCADE
        )
    """)
    
    # Create FIELD_AGENT table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS FIELD_AGENT (
            agent_code INTEGER PRIMARY KEY,
            person_id INTEGER UNIQUE,
            center_code INTEGER,
            is_active TEXT DEFAULT 'YES',
            join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(person_id) REFERENCES PERSON(person_id) ON DELETE CASCADE
        )
    """)
    
    # Create IFARMER_CENTER table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS IFARMER_CENTER (
            center_code INTEGER PRIMARY KEY,
            center_name TEXT NOT NULL,
            upazila TEXT,
            district TEXT
        )
    """)
    
    # Create KYC table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS KYC (
            kyc_id INTEGER PRIMARY KEY AUTOINCREMENT,
            farmer_code INTEGER,
            agent_code INTEGER,
            identity_verified TEXT DEFAULT 'PENDING' CHECK(identity_verified IN ('PENDING', 'VERIFIED', 'REJECTED')),
            verification_date TIMESTAMP,
            FOREIGN KEY(farmer_code) REFERENCES FARMER(farmer_code)
        )
    """)
    
    # Create LOAN table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS LOAN (
            loan_no INTEGER PRIMARY KEY AUTOINCREMENT,
            farmer_code INTEGER,
            amount REAL DEFAULT 50000,
            purpose TEXT DEFAULT 'কৃষি উৎপাদন ও সার-বীজ ক্রয়',
            loan_state TEXT DEFAULT 'PENDING' CHECK(loan_state IN ('PENDING', 'ACTIVE', 'CLOSED', 'REJECTED')),
            approval_date TIMESTAMP,
            application_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            tenure_months INTEGER,
            FOREIGN KEY(farmer_code) REFERENCES FARMER(farmer_code)
        )
    """)
    
    # Create PURCHASE table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS PURCHASE (
            purchase_id INTEGER PRIMARY KEY AUTOINCREMENT,
            farmer_code INTEGER,
            agent_code INTEGER,
            payment_status TEXT DEFAULT 'PENDING' CHECK(payment_status IN ('PENDING', 'CONFIRMED', 'DELIVERED', 'CANCELLED')),
            purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(farmer_code) REFERENCES FARMER(farmer_code)
        )
    """)
    
    # Create INVENTORY table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS INVENTORY (
            inventory_id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_code INTEGER,
            item_name TEXT NOT NULL,
            quantity INTEGER,
            unit TEXT,
            price REAL,
            FOREIGN KEY(agent_code) REFERENCES FIELD_AGENT(agent_code)
        )
    """)
    
    # Create ADVISOR table (Enhanced Advisor Profile)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ADVISOR (
            advisor_id INTEGER PRIMARY KEY,
            person_id INTEGER UNIQUE,
            specialization TEXT NOT NULL,
            bio TEXT,
            experience_years INTEGER,
            qualification TEXT,
            is_available TEXT DEFAULT 'YES',
            profile_image TEXT,
            rating REAL DEFAULT 5.0,
            total_bookings INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(person_id) REFERENCES PERSON(person_id) ON DELETE CASCADE
        )
    """)
    
    # Create ADVISOR_RATE table (Hourly & Daily Rates)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ADVISOR_RATE (
            rate_id INTEGER PRIMARY KEY AUTOINCREMENT,
            advisor_id INTEGER NOT NULL,
            rate_type TEXT NOT NULL CHECK(rate_type IN ('HOURLY', 'DAILY')),
            amount REAL NOT NULL,
            currency TEXT DEFAULT 'BDT',
            min_duration INTEGER,
            max_duration INTEGER,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(advisor_id) REFERENCES ADVISOR(advisor_id) ON DELETE CASCADE
        )
    """)
    
    # Create ADVISOR_AVAILABILITY table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ADVISOR_AVAILABILITY (
            availability_id INTEGER PRIMARY KEY AUTOINCREMENT,
            advisor_id INTEGER NOT NULL,
            day_of_week TEXT,
            start_time TEXT,
            end_time TEXT,
            is_available TEXT DEFAULT 'YES',
            FOREIGN KEY(advisor_id) REFERENCES ADVISOR(advisor_id) ON DELETE CASCADE
        )
    """)
    
    # Create ADVISOR_BOOKING table (Main Booking System)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ADVISOR_BOOKING (
            booking_id INTEGER PRIMARY KEY AUTOINCREMENT,
            advisor_id INTEGER NOT NULL,
            farmer_id INTEGER NOT NULL,
            agent_id INTEGER,
            booking_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            scheduled_date TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            duration_hours REAL,
            rate_type TEXT NOT NULL CHECK(rate_type IN ('HOURLY', 'DAILY')),
            total_amount REAL NOT NULL,
            payment_status TEXT DEFAULT 'PENDING' CHECK(payment_status IN ('PENDING', 'PAID', 'CANCELLED', 'REFUNDED')),
            booking_status TEXT DEFAULT 'CONFIRMED' CHECK(booking_status IN ('PENDING', 'CONFIRMED', 'COMPLETED', 'CANCELLED')),
            consultation_topic TEXT,
            notes TEXT,
            FOREIGN KEY(advisor_id) REFERENCES ADVISOR(advisor_id) ON DELETE CASCADE,
            FOREIGN KEY(farmer_id) REFERENCES FARMER(farmer_code) ON DELETE CASCADE
        )
    """)
    
    # Create ADVISOR_RATING table (Reviews & Ratings)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ADVISOR_RATING (
            rating_id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_id INTEGER NOT NULL,
            advisor_id INTEGER NOT NULL,
            farmer_id INTEGER NOT NULL,
            rating INTEGER CHECK(rating >= 1 AND rating <= 5),
            review TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(booking_id) REFERENCES ADVISOR_BOOKING(booking_id) ON DELETE CASCADE,
            FOREIGN KEY(advisor_id) REFERENCES ADVISOR(advisor_id) ON DELETE CASCADE,
            FOREIGN KEY(farmer_id) REFERENCES FARMER(farmer_code) ON DELETE CASCADE
        )
    """)
    
    # Create NOTIFICATION table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS NOTIFICATION (
            notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            link TEXT,
            is_read INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(person_id) REFERENCES PERSON(person_id) ON DELETE CASCADE
        )
    """)
    
    # Create COMMUNITY_POST table (Admin & Agent broadcasts)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS COMMUNITY_POST (
            post_id INTEGER PRIMARY KEY AUTOINCREMENT,
            author_id INTEGER,
            title TEXT,
            content TEXT NOT NULL,
            post_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(author_id) REFERENCES PERSON(person_id) ON DELETE SET NULL
        )
    """)
    
    conn.commit()
    print(f"Database initialized successfully at {db_path}")
    cursor.close()
    conn.close()

if __name__ == "__main__":
    init_database()
