
import sqlite3
from config import Config

def simulate_plagiarism():
    print(f"Connecting to {Config.DATABASE_PATH}...")
    conn = sqlite3.connect(Config.DATABASE_PATH)
    cursor = conn.cursor()
    
    # 1. Check if columns exist
    cursor.execute("PRAGMA table_info(problem_submissions)")
    columns = [row[1] for row in cursor.fetchall()]
    print(f"Columns: {columns}")
    
    if 'is_plagiarized' not in columns:
        print("ERROR: is_plagiarized column missing! proper migration needed.")
        return

    # 2. Get latest submission
    cursor.execute("SELECT id, student_id FROM problem_submissions ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    
    if row:
        sub_id = row[0]
        student_id = row[1]
        print(f"Found submission {sub_id} by student {student_id}")
        
        # 3. Mark as plagiarized
        try:
            cursor.execute("""
                UPDATE problem_submissions 
                SET is_plagiarized = 1, 
                    plagiarism_score = 0.98, 
                    status = 'rejected',
                    ai_feedback = 'Simulated Plagiarism Detected for testing.'
                WHERE id = ?
            """, (sub_id,))
            conn.commit()
            print(f"SUCCESS: Marked submission {sub_id} as PLAGIARIZED.")
        except Exception as e:
            print(f"Error updating: {e}")
    else:
        print("No submissions found. Creating a dummy one...")
        # Create a dummy submission if needed, but better to ask user to submit.
        # But I can insert one.
        # Need a valid problem_id and student_id? All FKs.
        pass

    conn.close()

if __name__ == "__main__":
    simulate_plagiarism()
