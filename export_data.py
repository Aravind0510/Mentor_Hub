import sqlite3
import json
from datetime import datetime

def datetime_handler(x):
    if isinstance(x, datetime):
        return x.isoformat()
    return str(x)

def export_all_tables():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get list of all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row['name'] for row in cursor.fetchall() if row['name'] != 'sqlite_sequence']
    
    db_export = {}

    for table in tables:
        print(f"Exporting table: {table}...")
        cursor.execute(f"SELECT * FROM {table}")
        rows = cursor.fetchall()
        db_export[table] = [dict(row) for row in rows]

    with open('database_export.json', 'w', encoding='utf-8') as f:
        json.dump(db_export, f, indent=4, default=datetime_handler)

    print("\n✅ Success! All data has been extracted to 'database_export.json'")
    conn.close()

if __name__ == '__main__':
    export_all_tables()
