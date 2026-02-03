import os
import psycopg2
from psycopg2.extras import DictCursor
from config import Config
from werkzeug.security import generate_password_hash

def get_db():
    conn = psycopg2.connect(Config.DATABASE_URL, cursor_factory=DictCursor)
    return conn

def init_db():
    """Initialize database tables for PostgreSQL if they don't exist"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            name TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin', 'mentor', 'student')),
            mentor_id INTEGER REFERENCES users(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tasks table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id SERIAL PRIMARY KEY,
            mentor_id INTEGER NOT NULL REFERENCES users(id),
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            due_date TIMESTAMP,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Problems table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS problems (
            id SERIAL PRIMARY KEY,
            mentor_id INTEGER NOT NULL REFERENCES users(id),
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            problem_type TEXT NOT NULL CHECK(problem_type IN ('coding', 'sql')),
            language TEXT,
            difficulty TEXT DEFAULT 'medium' CHECK(difficulty IN ('easy', 'medium', 'hard')),
            test_cases TEXT,
            expected_output TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            constraints TEXT
        )
    ''')
    
    # Task Submissions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS task_submissions (
            id SERIAL PRIMARY KEY,
            task_id INTEGER NOT NULL REFERENCES tasks(id),
            student_id INTEGER NOT NULL REFERENCES users(id),
            file_path TEXT,
            content TEXT,
            submission_type TEXT NOT NULL CHECK(submission_type IN ('file', 'editor')),
            status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'accepted', 'rejected')),
            score INTEGER DEFAULT 0,
            ai_feedback TEXT,
            ai_explanation TEXT,
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Problem Submissions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS problem_submissions (
            id SERIAL PRIMARY KEY,
            problem_id INTEGER NOT NULL REFERENCES problems(id),
            student_id INTEGER NOT NULL REFERENCES users(id),
            code TEXT NOT NULL,
            language TEXT NOT NULL,
            file_path TEXT,
            submission_type TEXT NOT NULL CHECK(submission_type IN ('file', 'editor')),
            status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'accepted', 'rejected')),
            score INTEGER DEFAULT 0,
            execution_result TEXT,
            ai_feedback TEXT,
            ai_explanation TEXT,
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            focus_lost_count INTEGER DEFAULT 0,
            paste_attempts INTEGER DEFAULT 0,
            is_plagiarized BOOLEAN DEFAULT FALSE,
            plagiarism_score FLOAT DEFAULT 0.0,
            plagiarism_source_name TEXT,
            plagiarism_source_student_id INTEGER
        )
    ''')
    
    # Aptitude Tests table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS aptitude_tests (
            id SERIAL PRIMARY KEY,
            mentor_id INTEGER NOT NULL REFERENCES users(id),
            title TEXT NOT NULL,
            description TEXT,
            duration INTEGER DEFAULT 30,
            questions TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            end_time TIMESTAMP
        )
    ''')
    
    # Aptitude Submissions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS aptitude_submissions (
            id SERIAL PRIMARY KEY,
            student_id INTEGER NOT NULL REFERENCES users(id),
            test_id INTEGER NOT NULL REFERENCES aptitude_tests(id),
            score INTEGER DEFAULT 0,
            total_questions INTEGER DEFAULT 0,
            answers TEXT,
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            focus_lost_count INTEGER DEFAULT 0,
            paste_attempts INTEGER DEFAULT 0
        )
    ''')
    
    # Activity Logs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS activity_logs (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            action TEXT NOT NULL,
            details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print("PostgreSQL Database initialized successfully!")

def seed_db():
    """Dummy seed_db for compatibility"""
    pass

if __name__ == '__main__':
    init_db()
