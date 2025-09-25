import os

from psycopg2.pool import SimpleConnectionPool

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:ankit123@localhost:5432/hostel_report")

# Create pool sizes as needed
db_pool = SimpleConnectionPool(1, 10, DATABASE_URL)

def get_db_connection():
    """ Get a DB connection from pool """
    return db_pool.getconn()

def release_db_connection(conn):
    """ Return the connection to the pool """
    db_pool.putconn(conn)
