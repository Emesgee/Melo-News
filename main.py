# app/main.py
from app import create_app

if __name__ == "__main__":
    app = create_app()
    # This line allows the Flask app to listen on all interfaces (0.0.0.0) on port 5000
    app.run(host='0.0.0.0', port=5000, debug=True)
