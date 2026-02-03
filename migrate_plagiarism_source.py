
import sqlite3
from config import Config

def add_source_student_column():
    print("Migrating database for source student tracking...")
    conn = sqlite3.connect(Config.DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        # Add plagiarism_source_student_id column
        try:
            cursor.execute("ALTER TABLE problem_submissions ADD COLUMN plagiarism_source_student_id INTEGER")
            print("Added plagiarism_source_student_id column")
        except sqlite3.OperationalError:
            print("plagiarism_source_student_id column already exists")
            
        conn.commit()
        print("Migration complete!")
    except Exception as e:
        print(f"Migration failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    add_source_student_column()
