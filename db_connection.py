import os
from dotenv import load_dotenv
from psycopg2.pool import SimpleConnectionPool

load_dotenv()

# Use DATABASE_URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    # Fallback for local development if .env is not loaded or missing
    print("WARNING: DATABASE_URL environment variable is not set. Using default for local development.")
    # Assuming the local default from the .env file is the intended local connection string
    DATABASE_URL = "postgresql://postgres:ankit123@localhost:5432/hostel_report"

# Fix for Render/psycopg2 compatibility: replace 'postgres://' with 'postgresql://'
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Create pool sizes as needed
# Note: If this file is not imported, this pool is unused.
db_pool = SimpleConnectionPool(1, 10, DATABASE_URL)

def get_db_connection():
    """ Get a DB connection from pool """
    return db_pool.getconn()

def release_db_connection(conn):
    """ Return the connection to the pool """
    db_pool.putconn(conn)
