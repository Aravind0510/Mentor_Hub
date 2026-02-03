import psycopg2, os
from dotenv import load_dotenv

load_dotenv()
conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

# Check if column exists
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'aptitude_tests' AND column_name = 'attempt_limit'")
if not cur.fetchone():
    print("Adding attempt_limit column to aptitude_tests table...")
    cur.execute("ALTER TABLE aptitude_tests ADD COLUMN attempt_limit INTEGER DEFAULT 1")
    conn.commit()
    print("Column added successfully.")
else:
    print("Column attempt_limit already exists.")

conn.close()
