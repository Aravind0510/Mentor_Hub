import json
import psycopg2
from psycopg2.extras import execute_values
import os
from dotenv import load_dotenv
import time

load_dotenv()

def get_conn():
    return psycopg2.connect(os.getenv('DATABASE_URL'))

def migrate():
    log_file = open('migration_debug.log', 'w', encoding='utf-8')
    def log(msg):
        print(msg)
        log_file.write(msg + '\n')
        log_file.flush()

    log("Starting robust migration...")
    
    with open('database_export.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    table_order = [
        'users',
        'tasks',
        'problems',
        'task_submissions',
        'problem_submissions',
        'activity_logs',
        'aptitude_tests',
        'aptitude_submissions'
    ]

    log("Clearing target tables (Cascading)...")
    try:
        conn = get_conn()
        cursor = conn.cursor()
        for table in reversed(table_order):
            try:
                cursor.execute(f"TRUNCATE TABLE {table} CASCADE")
                log(f"--- Truncated {table}")
            except Exception as e:
                log(f"--- Skip truncate {table}: {e}")
        conn.commit()
        conn.close()
    except Exception as e:
        log(f"FAIL to clear tables: {e}")
        return

    for table in table_order:
        if table not in data:
            log(f"--- Skipping {table} (no data)")
            continue
            
        rows = data[table]
        if not rows:
            log(f"--- No rows for {table}")
            continue

        log(f"--- Migrating {len(rows)} rows to {table}...")
        
        try:
            conn = get_conn()
            cursor = conn.cursor()
            
            columns = list(rows[0].keys())
            
            # Build values and handle Type conversions
            processed_values = []
            for row in rows:
                row_values = []
                for col in columns:
                    val = row[col]
                    # Conversion: Boolean coercion for PostgreSQL
                    if table == 'problem_submissions' and col == 'is_plagiarized':
                        val = bool(val)
                    row_values.append(val)
                processed_values.append(row_values)

            query = f"INSERT INTO {table} ({', '.join(columns)}) VALUES %s"
            
            batch_size = 50
            for i in range(0, len(processed_values), batch_size):
                batch = processed_values[i:i + batch_size]
                execute_values(cursor, query, batch)
                conn.commit()
                log(f"    - Processed batch {i//batch_size + 1}")

            log(f"--- SUCCESS: {table}")
            
            # Reset sequence
            try:
                cursor.execute(f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), COALESCE(MAX(id), 1), true) FROM {table}")
                conn.commit()
            except Exception as seq_e:
                log(f"    - Warning reset sequence: {seq_e}")
                conn.rollback()

            conn.close()
            time.sleep(1)
            
        except Exception as e:
            log(f"!!! ERROR {table}: {e}")
            if 'conn' in locals() and not conn.closed:
                conn.rollback()
                conn.close()

    log_file.close()
    print("\nRobust Migration Done. Check migration_debug.log")

if __name__ == '__main__':
    migrate()
