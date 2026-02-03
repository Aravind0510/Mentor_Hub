import sqlite3
from config import Config

def migrate():
    print(f"Connecting to {Config.DATABASE_PATH}")
    conn = sqlite3.connect(Config.DATABASE_PATH)
    cursor = conn.cursor()
    
    # Check aptitude_submissions
    try:
        cursor.execute("ALTER TABLE aptitude_submissions ADD COLUMN focus_lost_count INTEGER DEFAULT 0")
        print("Added focus_lost_count to aptitude_submissions")
    except Exception as e:
        print(f"aptitude_submissions focus error (likely exists): {e}")

    try:
        cursor.execute("ALTER TABLE aptitude_submissions ADD COLUMN paste_attempts INTEGER DEFAULT 0")
        print("Added paste_attempts to aptitude_submissions")
    except Exception as e:
        print(f"aptitude_submissions paste error (likely exists): {e}")
    
    conn.commit()
    conn.close()

if __name__ == '__main__':
    migrate()
