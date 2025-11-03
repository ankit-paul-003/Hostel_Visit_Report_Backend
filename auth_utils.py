from dotenv import load_dotenv
import os
load_dotenv()

import datetime
import jwt

# Use an env var in production
SECRET_KEY = os.getenv('FLASK_SECRET_KEY')

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
