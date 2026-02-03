
import sqlite3
from config import Config

def migrate_aptitude():
    print("Migrating database for Aptitude Tests...")
    conn = sqlite3.connect(Config.DATABASE_PATH)
    cursor = conn.cursor()
    
    # Aptitude Tests Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS aptitude_tests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mentor_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            duration INTEGER DEFAULT 30,
            questions TEXT NOT NULL, -- JSON array of questions
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (mentor_id) REFERENCES users (id)
        )
    ''')
    print("Created 'aptitude_tests' table.")

    # Aptitude Submissions Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS aptitude_submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            test_id INTEGER NOT NULL,
            score INTEGER DEFAULT 0,
            total_questions INTEGER DEFAULT 0,
            answers TEXT, -- JSON of student answers
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES users (id),
            FOREIGN KEY (test_id) REFERENCES aptitude_tests (id)
        )
    ''')
    print("Created 'aptitude_submissions' table.")

    conn.commit()
    conn.close()
    print("Migration complete!")

if __name__ == "__main__":
    migrate_aptitude()
