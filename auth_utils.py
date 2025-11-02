<<<<<<< HEAD
=======
from dotenv import load_dotenv
import os
load_dotenv()

>>>>>>> 4efd6c871f2d2a90e6126f0e1cf9fc57364d4534
import datetime

import jwt

# Use an env var in production
<<<<<<< HEAD
SECRET_KEY = "your_secret_key_here_change_in_prod"
=======
SECRET_KEY = os.getenv('FLASK_SECRET_KEY')
>>>>>>> 4efd6c871f2d2a90e6126f0e1cf9fc57364d4534

def generate_token(user_type, username, hours_valid=3):
    payload = {
        "user_type": user_type,
        "username": username,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=hours_valid)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def verify_token(token):
    """ Verify JWT token and return decoded payload or None """
    try:
        decoded = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return decoded
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
