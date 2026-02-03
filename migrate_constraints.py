
import sqlite3
import json
from config import Config

def add_constraints_column():
    print("Migrating database for problem constraints...")
    conn = sqlite3.connect(Config.DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        # Add constraints column (JSON string)
        try:
            cursor.execute("ALTER TABLE problems ADD COLUMN constraints TEXT")
            print("Added constraints column")
            
            # Set default constraints (empty dict) for existing problems
            default_constraints = json.dumps({
                'block_paste': False,
                'disable_hints': False,
                'track_focus': False
            })
            cursor.execute("UPDATE problems SET constraints = ?", (default_constraints,))
            
        except sqlite3.OperationalError:
            print("constraints column already exists")
            
        conn.commit()
        print("Migration complete!")
    except Exception as e:
        print(f"Migration failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    add_constraints_column()
