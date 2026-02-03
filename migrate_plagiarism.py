
import sqlite3
from config import Config

def add_plagiarism_columns():
    print("Migrating database...")
    conn = sqlite3.connect(Config.DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        # Add is_plagiarized column
        try:
            cursor.execute("ALTER TABLE problem_submissions ADD COLUMN is_plagiarized INTEGER DEFAULT 0")
            print("Added is_plagiarized column")
        except sqlite3.OperationalError:
            print("is_plagiarized column already exists")
            
        # Add plagiarism_score column
        try:
            cursor.execute("ALTER TABLE problem_submissions ADD COLUMN plagiarism_score REAL DEFAULT 0.0")
            print("Added plagiarism_score column")
        except sqlite3.OperationalError:
            print("plagiarism_score column already exists")
            
        conn.commit()
        print("Migration complete!")
    except Exception as e:
        print(f"Migration failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    add_plagiarism_columns()
