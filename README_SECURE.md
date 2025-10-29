# Backend_Secure (cleaned)

This archive was automatically cleaned to make it **safe to upload to GitHub**.
**DO NOT** commit any real secrets. Instead, set them in your hosting environment
or in a local `.env` file which must never be committed.

## What I changed
- Removed any `credentials.json` files found in the project.
- Replaced occurrences of the literal PostgreSQL connection string(s) with calls to `os.getenv('DATABASE_URL')`.
- Inserted dotenv loader (`from dotenv import load_dotenv; import os; load_dotenv()`) where necessary so that code reads environment variables.
- Added a `.env.template` file showing the expected variables (FLASK_SECRET_KEY, DATABASE_URL, GOOGLE_DRIVE_CREDENTIALS_JSON).
- Added a `.gitignore` to keep `.env` and credential files out of GitHub.
- (Files modified): [
  "Backend/app.py",
  "Backend/auth_utils.py",
  "Backend/db_connection.py"
]

## How to use
1. Create a local `.env` (not committed) using `.env.template` as a guide.
2. Put your real `DATABASE_URL` and `FLASK_SECRET_KEY` in `.env`.
   Example:
     DATABASE_URL=postgresql://postgres:your_password@localhost:5432/hostel_report
3. For Google Drive credentials you can either:
   - Upload the `credentials.json` to your server and set GOOGLE_DRIVE_CREDENTIALS_FILE=/path/to/credentials.json
   - Or store the full credentials JSON in the env var `GOOGLE_DRIVE_CREDENTIALS_JSON` (copy-paste the JSON content).
4. Deploy to Render/Railway and set the environment variables in the service dashboard.

## Notes
- Double-check any 3rd-party library config (e.g., SQLAlchemy) — they should read DATABASE_URL from env.
- If you want, I can also replace explicit `psycopg2.connect(...)` calls with SQLAlchemy engine creation that uses `os.getenv('DATABASE_URL')`.
