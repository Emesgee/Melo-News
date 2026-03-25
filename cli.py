"""Entry point for the `backend` CLI command."""
import os
import sys

# Ensure the project root is on the path so `app` and `main` are importable
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def main():
    from dotenv import load_dotenv
    load_dotenv()

    from app import create_app, socketio

    app = create_app()

    with app.app_context():
        from app.models import db
        try:
            db.create_all()
            print("Tables created successfully.")
        except Exception as e:
            print(f"An error occurred while creating tables: {e}")

    env = os.getenv("ENVIRONMENT", "development").lower()
    if env == "production":
        print("[WARNING] Use gunicorn or uwsgi for production. Running dev server.")
        socketio.run(app, host="0.0.0.0", port=5000, debug=False)
    else:
        socketio.run(app, host="0.0.0.0", port=5000, debug=True, allow_unsafe_werkzeug=True)


if __name__ == "__main__":
    main()
