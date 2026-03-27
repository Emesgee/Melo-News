from app import create_app, socketio
from app.models import db
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Create the app instance
app = create_app()

# Create tables within the application context
with app.app_context():
    try:
        # Create all tables in the PostgreSQL database
        db.create_all()  
        print("Tables created successfully.")
    except Exception as e:
        print(f"An error occurred while creating tables: {e}")

if __name__ == "__main__":
    import os
    env = os.getenv('ENVIRONMENT', 'development').lower()
    if env == 'production':
        # In production, use a proper WSGI server (gunicorn/uwsgi) instead
        print("[WARNING] Use gunicorn or uwsgi for production. Running dev server.")
        socketio.run(app, host="0.0.0.0", port=5000, debug=False)
    else:
        socketio.run(app, host="0.0.0.0", port=5000, debug=True, allow_unsafe_werkzeug=True)
