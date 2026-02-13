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
    # Bind only to localhost; Nginx proxies requests to this port
    socketio.run(app, host="127.0.0.1", port=8000, debug=True, allow_unsafe_werkzeug=True)