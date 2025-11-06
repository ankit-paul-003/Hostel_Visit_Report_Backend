import os
import datetime
import os
from io import BytesIO

import jwt
import pandas as pd
import psycopg2
from flask import Flask, Response, jsonify, request
from urllib.parse import urlparse
from flask_cors import CORS
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from psycopg2.extras import RealDictCursor

# ------------------------------ #
# Google Drive API Configuration #
# ------------------------------ #
SCOPES = ['https://www.googleapis.com/auth/drive']
SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_CREDENTIALS", "hostelmanagement-455018-5e40c6a6113c.json")
UPLOAD_FOLDER_ID = os.getenv("UPLOAD_FOLDER_ID", "1-bPtMwp6rPE3D2yqmk5qnq8Ytvl_O07A")

creds = None
drive_service = None

try:
    # Support loading Google service account credentials from an environment variable
    # (recommended for hosted environments like Render). If `GOOGLE_DRIVE_CREDENTIALS_JSON`
    # is set, it should contain the full JSON contents of the service account file.
    ga_json = os.getenv("GOOGLE_DRIVE_CREDENTIALS_JSON")
    if ga_json:
        import json
        ga_json_str = ga_json.strip()
        # If the env var contains JSON text, parse it. If it contains a filename
        # (for example someone placed the filename, possibly wrapped in braces
        # like "{hostelmanagement-...json}"), load from that file. Otherwise
        # raise a helpful error.
        if ga_json_str.startswith("{") and '"' in ga_json_str:
            # Likely actual JSON (contains double quotes)
            try:
                info = json.loads(ga_json_str)
                creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
            except Exception as e:
                raise RuntimeError("Failed to parse GOOGLE_DRIVE_CREDENTIALS_JSON: {}".format(e))
        else:
            # Treat value as a filename (strip surrounding braces or quotes if present)
            candidate = ga_json_str.strip().strip('{}').strip('"').strip("'")
            if os.path.isfile(candidate):
                creds = service_account.Credentials.from_service_account_file(candidate, scopes=SCOPES)
            else:
                raise RuntimeError(
                    "GOOGLE_DRIVE_CREDENTIALS_JSON is set but is not valid JSON nor a path to a file: '{}'".format(ga_json_str)
                )
    else:
        # Fall back to loading from a file path (useful for local development only)
        creds_path = SERVICE_ACCOUNT_FILE
        creds = service_account.Credentials.from_service_account_file(creds_path, scopes=SCOPES)

    if creds:
        drive_service = build('drive', 'v3', credentials=creds)
    else:
        print("WARNING: Google Drive credentials could not be loaded.")

except Exception as e:
    print(f"WARNING: Failed to initialize Google Drive service due to credential error: {e}")
    drive_service = None

# ------------------------------ #
# Flask Setup                    #
# ------------------------------ #
app = Flask(__name__)
# Configure CORS to allow requests from your frontend domains
# Define allowed origins
ALLOWED_ORIGINS = [
    "https://hostel-visit-report-frontend.vercel.app",
    "http://localhost:5173"
]
CORS(app, supports_credentials=True, origins=ALLOWED_ORIGINS)
SECRET_KEY = os.getenv('FLASK_SECRET_KEY')  # Use a strong key in production

# ------------------------------ #
# Database Connection            #
# ------------------------------ #
def get_db_connection():
    conn_str = os.getenv("DATABASE_URL")
    if not conn_str:
        # If DATABASE_URL is not set, we cannot connect to the remote database.
        print("ERROR: DATABASE_URL environment variable is not set.")
        raise RuntimeError("DATABASE_URL environment variable is not set.")
    
    # Fix for Render/psycopg2 compatibility: replace 'postgres://' with 'postgresql://'
    if conn_str.startswith("postgres://"):
        conn_str = conn_str.replace("postgres://", "postgresql://", 1)
        
    # Note: We avoid printing the full connection string for security, but confirm its presence.
    parsed_url = urlparse(conn_str)
    print(f"INFO: Attempting database connection to host: {parsed_url.hostname} on port: {parsed_url.port}")
    return psycopg2.connect(conn_str)

# ------------------------------ #
# JWT Token                      #
# ------------------------------ #
def generate_token(user_type, username):
    payload = {
        "user_type": user_type,
        "username": username,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=3)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def verify_token(token):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


# main route
@app.route('/')
def index():
    return "Hostel Management Backend is running."
# ------------------------------ #
# Teacher Login                  #
# ------------------------------ #
@app.route('/teacher-login', methods=['POST', 'OPTIONS'])
def teacher_login():
    if request.method == 'OPTIONS':
        # Preflight request, Flask-CORS should handle this, but we ensure a 200 OK response if it reaches here
        return jsonify({'message': 'Preflight success'}), 200
    
    data = request.json
    teacher_id = data.get("teacherId")
    password = data.get("password")

    if not teacher_id or not password:
        return jsonify({"success": False, "message": "Missing credentials"}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT name FROM teachers WHERE name = %s AND password = %s", (teacher_id, password))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user:
            token = generate_token("teacher", teacher_id)
            return jsonify({"success": True, "message": "Login successful", "token": token})

        return jsonify({"success": False, "message": "Invalid credentials"}), 401
    except Exception as e:
        # Log the error for debugging on the server side
        print(f"Teacher login database error: {e}")
        return jsonify({"success": False, "message": "Internal server error"}), 500

# ------------------------------ #
# Admin Login                    #
# ------------------------------ #
@app.route('/admin-login', methods=['POST', 'OPTIONS'])
def admin_login():
    if request.method == 'OPTIONS':
        # Preflight request, Flask-CORS should handle this, but we ensure a 200 OK response if it reaches here
        return jsonify({'message': 'Preflight success'}), 200
    
    data = request.json
    admin_id = data.get("adminId")
    password = data.get("password")

    if not admin_id or not password:
        return jsonify({"success": False, "message": "Missing credentials"}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT name FROM admins WHERE name = %s AND password = %s", (admin_id, password))
        user = cur.fetchone()
        cur.close()
        conn.close()

        # Special Admin
        if user:
            user_type = "Paul" if admin_id == "Paul" and password == "1234" else "admin" 
            token = generate_token(user_type, admin_id)
            return jsonify({"success": True, "message": "Login successful", "token": token})

        return jsonify({"success": False, "message": "Invalid credentials"}), 401
    except Exception as e:
        # Log the error for debugging on the server side
        print(f"Admin login database error: {e}")
        return jsonify({"success": False, "message": "Internal server error"}), 500

# ------------------------------ #
# Get Teachers                   #
# ------------------------------ #
@app.route('/teachers', methods=['GET'])
def get_teachers():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT id, name FROM teachers")
    teachers = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify(teachers)

# ------------------------------ #
# Get Reports                    #
# ------------------------------ #
@app.route('/forms', methods=['GET'])
def get_forms():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM reports")
    forms = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify(forms)

# ------------------------------ #
# Submit Form                    #
# ------------------------------ #
@app.route('/submit-form', methods=['POST'])
def submit_form():
    token = request.headers.get("Authorization")
    if not token or not token.startswith("Bearer "):
        return jsonify({"success": False, "message": "Missing or invalid token"}), 403

    token = token.split("Bearer ")[1]
    decoded_token = verify_token(token)
    if not decoded_token or decoded_token.get("user_type") != "teacher":
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    teacher_name = request.form.get("teacherName")
    subordinate_teacher_name = request.form.get("subordinateTeacherName")
    hostel_name = request.form.get("hostelName")
    general_comments = request.form.get("generalComments")
    maintenance_required = request.form.get("maintenanceRequired")
    complaints = request.form.get("complaints")

    if not (teacher_name and subordinate_teacher_name and hostel_name):
        return jsonify({"success": False, "message": "Missing form fields"}), 400

    image_url = None
    if 'image' in request.files:
        image_file = request.files['image']
        if image_file:
            if not drive_service:
                return jsonify({"success": False, "message": "Image upload failed: Google Drive service not initialized"}), 500
            try:
                file_metadata = {'name': image_file.filename, 'parents': [UPLOAD_FOLDER_ID]}
                media = MediaIoBaseUpload(image_file, mimetype=image_file.mimetype, resumable=True)
                uploaded_file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
                image_url = f"https://drive.google.com/uc?id={uploaded_file.get('id')}"
            except Exception as e:
                return jsonify({"success": False, "message": "Image upload failed", "error": str(e)}), 500

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO reports (teacher_name, subordinate_teacher_name, hostel_name, 
                    general_comments, maintenance_required, complaints, image_url, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
            """, (teacher_name, subordinate_teacher_name, hostel_name,
                  general_comments, maintenance_required, complaints, image_url))
            conn.commit()
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

    return jsonify({"success": True, "message": "Form submitted successfully"}), 200

# ------------------------------ #
# Add Teacher                    #
# ------------------------------ #
@app.route('/add-teacher', methods=['POST'])
def add_teacher():
    data = request.json
    teacher_name = data.get("name")
    password = data.get("password")

    if not teacher_name or not password:
        return jsonify({"error": "Missing fields"}), 400

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO teachers (name, password) VALUES (%s, %s)", (teacher_name, password))
        conn.commit()
    except psycopg2.Error as e:
        return jsonify({"error": "Database error", "details": str(e)}), 500
    finally:
        cur.close()
        conn.close()

    return jsonify({"message": "Teacher added successfully"}), 201

# ------------------------------ #
# Delete Teacher                 #
# ------------------------------ #
@app.route('/delete-teacher/<int:teacher_id>', methods=['DELETE', 'OPTIONS'])
def delete_teacher(teacher_id):
    if request.method == 'OPTIONS':
        return jsonify({'message': 'Preflight success'}), 200
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM teachers WHERE id = %s", (teacher_id,))
        conn.commit()
        return jsonify({"message": "Teacher deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": "Failed to delete teacher"}), 500
    finally:
        cur.close()
        conn.close()

# ------------------------------ #
# Delete Form (Only Paul)        #
# ------------------------------ #
@app.route('/delete-form/<int:form_id>', methods=['DELETE', 'OPTIONS'])
def delete_form(form_id):
    if request.method == 'OPTIONS':
        return jsonify({'message': 'Preflight success'}), 200
    token = request.headers.get("Authorization")
    if not token:
        return jsonify({"success": False, "message": "Unauthorized - No token provided"}), 401

    decoded_token = verify_token(token.split("Bearer ")[1])
    if not decoded_token or decoded_token.get("user_type") != "Paul":
        return jsonify({"success": False, "message": "Unauthorized - Only Paul can delete forms"}), 403

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM reports WHERE id = %s", (form_id,))
        conn.commit()
    finally:
        cur.close()
        conn.close()

    return jsonify({"success": True, "message": "Form deleted successfully"})

# ------------------------------ #
# Get Admins                     #
# ------------------------------ #
@app.route('/admins', methods=['GET'])
def get_admins():
    token = request.headers.get("Authorization")
    if not token or not token.startswith("Bearer "):
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    decoded_token = verify_token(token.split("Bearer ")[1])
    if not decoded_token:
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT id, name FROM admins")
    admins = cur.fetchall()
    cur.close()
    conn.close()

    return jsonify(admins), 200

# ------------------------------ #
# Add Admin                       #
# ------------------------------ #
@app.route('/add-admin', methods=['POST'])
def add_admin():
    data = request.json
    name = data.get("name")
    password = data.get("password")

    if not name or not password:
        return jsonify({"error": "Missing fields"}), 400

    token = request.headers.get("Authorization")
    if not token:
        return jsonify({"error": "Unauthorized"}), 403

    decoded_token = verify_token(token.split("Bearer ")[1])
    if not decoded_token:
        return jsonify({"error": "Unauthorized"}), 403

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO admins (name, password) VALUES (%s, %s)", (name, password))
        conn.commit()
    except psycopg2.Error as e:
        return jsonify({"error": "Database error", "details": str(e)}), 500
    finally:
        cur.close()
        conn.close()

    return jsonify({"message": "Admin added successfully"}), 201

# ------------------------------ #
# Delete Admin                     #
# ------------------------------ #
@app.route('/delete-admin/<int:admin_id>', methods=['DELETE', 'OPTIONS'])
def delete_admin(admin_id):
    if request.method == 'OPTIONS':
        return jsonify({'message': 'Preflight success'}), 200
    token = request.headers.get("Authorization")
    if not token:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    decoded_token = verify_token(token.split("Bearer ")[1])
    if not decoded_token:
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM admins WHERE id = %s", (admin_id,))
        conn.commit()
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()

    return jsonify({"success": True, "message": "Admin deleted successfully"})





# ------------------------------ #
# Download Report                #
# ------------------------------ #
@app.route('/download/<string:period>', methods=['GET'])
def download_report(period):
    conn = get_db_connection()
    cur = conn.cursor()

    query = {
        "weekly": "SELECT * FROM reports WHERE created_at >= NOW() - INTERVAL '7 days'",
        "monthly": "SELECT * FROM reports WHERE created_at >= NOW() - INTERVAL '1 month'",
        "yearly": "SELECT * FROM reports WHERE created_at >= NOW() - INTERVAL '1 year'"
    }.get(period)

    if not query:
        return jsonify({"error": "Invalid period"}), 400

    cur.execute(query)
    rows = cur.fetchall()
    column_names = [desc[0] for desc in cur.description]

    cur.close()
    conn.close()

    if not rows:
        return jsonify({"error": "No data available"}), 404

    df = pd.DataFrame(rows, columns=column_names)
    
    # Fix: Convert timezone-aware datetimes to timezone-unaware for Excel compatibility
    if 'created_at' in df.columns:
        # Convert to timezone unaware
        df['created_at'] = df['created_at'].apply(lambda x: x.replace(tzinfo=None) if x is not None and pd.notna(x) and hasattr(x, 'tzinfo') else x)
        
    output = BytesIO()
    df.to_excel(output, index=False, engine='openpyxl')
    output.seek(0)

    return Response(
        output.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=report_{period}.xlsx"}
    )

# ------------------------------ #
# Run Server                     #
# ------------------------------ #
if __name__ == "__main__":
    # Get port from environment variable for Render deployment
    port = int(os.getenv("PORT", 8000))
    # Run with host '0.0.0.0' to accept external connections
    app.run(host='0.0.0.0', port=port, debug=False)
