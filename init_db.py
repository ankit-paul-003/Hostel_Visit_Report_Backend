import os
import psycopg2
from urllib.parse import urlparse

def get_db_connection():
    conn_str = os.getenv("DATABASE_URL")
    if not conn_str:
        raise RuntimeError("DATABASE_URL environment variable is not set.")
    
    # Fix for Render/psycopg2 compatibility
    if conn_str.startswith("postgres://"):
        conn_str = conn_str.replace("postgres://", "postgresql://", 1)
        
    return psycopg2.connect(conn_str)

def initialize_db():
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        print("Creating 'admins' table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL
            );
        """)
        
        print("Creating 'teachers' table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS teachers (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL
            );
        """)

        print("Creating 'reports' table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id SERIAL PRIMARY KEY,
                teacher_name VARCHAR(255) NOT NULL,
                subordinate_teacher_name VARCHAR(255),
                hostel_name VARCHAR(255) NOT NULL,
                general_comments TEXT,
                maintenance_required TEXT,
                complaints TEXT,
                image_url TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Insert default admin user (Paul/1234) as seen in app.py line 187
        print("Inserting default admin user (Paul/1234)...")
        cur.execute("""
            INSERT INTO admins (name, password) VALUES ('Paul', '1234')
            ON CONFLICT (name) DO NOTHING;
        """)
        
        conn.commit()
        print("Database initialization complete.")

    except Exception as e:
        print(f"Database initialization failed: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    initialize_db()