<<<<<<< HEAD
=======
from dotenv import load_dotenv
import os
load_dotenv()

>>>>>>> 4efd6c871f2d2a90e6126f0e1cf9fc57364d4534
import os

from psycopg2.pool import SimpleConnectionPool

<<<<<<< HEAD
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:ankit123@localhost:5432/hostel_report")
=======
DATABASE_URL = os.getenv("DATABASE_URL", "os.getenv('DATABASE_URL')")
>>>>>>> 4efd6c871f2d2a90e6126f0e1cf9fc57364d4534

# Create pool sizes as needed
db_pool = SimpleConnectionPool(1, 10, DATABASE_URL)

def get_db_connection():
    """ Get a DB connection from pool """
    return db_pool.getconn()

def release_db_connection(conn):
    """ Return the connection to the pool """
    db_pool.putconn(conn)
