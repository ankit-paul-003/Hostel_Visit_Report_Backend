import datetime
import os
from io import BytesIO

import jwt
import pandas as pd
import psycopg2
from flask import Flask, Response, jsonify, request
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

creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
drive_service = build('drive', 'v3', credentials=creds)

# ------------------------------ #
# Flask Setup                    #
# ------------------------------ #
app = Flask(__name__)
CORS(app, supports_credentials=True, resources={r"/*": {"origins": "http://localhost:5173"}})
SECRET_KEY = "your_secret_key_here"  # Use a strong key in production

# ------------------------------ #
# Database Connection            #
# ------------------------------ #
def get_db_connection():
    return psycopg2.connect(
        database="hostel_report",
        user="postgres",
        password="ankit123",
        host="localhost",
        port="5432"
    )

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

# ------------------------------ #
# Teacher Login                  #
# ------------------------------ #
@app.route('/teacher-login', methods=['POST'])
def teacher_login():
    data = request.json
    teacher_id = data.get("teacherId")
    password = data.get("password")

    if not teacher_id or not password:
        return jsonify({"success": False, "message": "Missing credentials"}), 400

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

# ------------------------------ #
# Admin Login                    #
# ------------------------------ #
@app.route('/admin-login', methods=['POST'])
def admin_login():
    data = request.json
    admin_id = data.get("adminId")
    password = data.get("password")

    if not admin_id or not password:
        return jsonify({"success": False, "message": "Missing credentials"}), 400

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT name FROM admins WHERE name = %s AND password = %s", (admin_id, password))
    user = cur.fetchone()
    cur.close()
    conn.close()

    if user:
        user_type = "Paul" if admin_id == "Paul" and password == "1234" else "admin"
        token = generate_token(user_type, admin_id)
        return jsonify({"success": True, "message": "Login successful", "token": token})

    return jsonify({"success": False, "message": "Invalid credentials"}), 401

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
    if request.method == "OPTIONS":
        response = jsonify({"message": "CORS preflight successful"})
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Methods", "DELETE, OPTIONS")
        response.headers.add("Access-Control-Allow-Headers", "Authorization, Content-Type")
        return response, 200

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
    if request.method == "OPTIONS":
        response = jsonify({"success": True, "message": "CORS preflight successful"})
        response.headers.add("Access-Control-Allow-Origin", "http://localhost:5173")
        response.headers.add("Access-Control-Allow-Methods", "DELETE, OPTIONS")
        response.headers.add("Access-Control-Allow-Headers", "Authorization, Content-Type")
        return response, 200

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

    response = jsonify({"success": True, "message": "Form deleted successfully"})
    response.headers.add("Access-Control-Allow-Origin", "http://localhost:5173")
    return response

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
    if request.method == "OPTIONS":
        response = jsonify({"message": "CORS preflight successful"})
        response.headers.add("Access-Control-Allow-Origin", "http://localhost:5173")
        response.headers.add("Access-Control-Allow-Methods", "DELETE, OPTIONS")
        response.headers.add("Access-Control-Allow-Headers", "Authorization, Content-Type")
        return response, 200

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

    response = jsonify({"success": True, "message": "Admin deleted successfully"})
    response.headers.add("Access-Control-Allow-Origin", "http://localhost:5173")
    return response





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
    app.run(debug=True)
