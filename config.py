import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'default_secret_key')
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'default_jwt_secret_key')
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL', 
        "postgresql://admin:admin@localhost:5432/mydb"  # Replace with your PostgreSQL credentials
        #'postgresql://admin:lelecafe@192.168.77.62:5432/mydb'  # Replace with your PostgreSQL credentials
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
