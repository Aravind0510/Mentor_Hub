import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def migrate():
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cur = conn.cursor()
    
    try:
        print("Checking violation_limit column...")
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='aptitude_tests' AND column_name='violation_limit'")
        if not cur.fetchone():
            print("Adding violation_limit column to aptitude_tests...")
            cur.execute("ALTER TABLE aptitude_tests ADD COLUMN violation_limit INTEGER DEFAULT 3")
            conn.commit()
            print("Column added successfully.")
        else:
            print("Column already exists.")
            
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
