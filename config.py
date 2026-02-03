import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    GROQ_API_KEY = os.getenv('GROQ_API_KEY', '')
    DATABASE_URL = os.getenv('DATABASE_URL')
    # Backup for local dev if needed, but primary is URL
    DATABASE_PATH = 'database.db'
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
