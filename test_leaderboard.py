import psycopg2
from psycopg2.extras import DictCursor
import os
from dotenv import load_dotenv

load_dotenv()

def test_query():
    try:
        conn = psycopg2.connect(os.getenv('DATABASE_URL'), cursor_factory=DictCursor)
        cursor = conn.cursor()
        
        print("Testing CTE student leaderboard query...")
        query = '''
            WITH student_stats AS (
                SELECT 
                    u.id, u.name, u.email, m.name as mentor_name, u.mentor_id, u.role,
                    COALESCE((SELECT COUNT(*) FROM task_submissions ts 
                              WHERE ts.student_id = u.id AND ts.status = 'accepted'), 0) as tasks_completed,
                    COALESCE((SELECT COUNT(*) FROM problem_submissions ps 
                              WHERE ps.student_id = u.id AND ps.status = 'accepted'), 0) as problems_solved,
                    COALESCE((SELECT COUNT(*) FROM aptitude_submissions aps WHERE aps.student_id = u.id), 0) as aptitude_completed,
                    COALESCE((SELECT AVG(score) FROM task_submissions ts WHERE ts.student_id = u.id), 0) as avg_task_score,
                    COALESCE((SELECT AVG(score) FROM problem_submissions ps WHERE ps.student_id = u.id), 0) as avg_problem_score,
                    COALESCE((SELECT AVG(CASE WHEN total_questions > 0 THEN (CAST(score AS FLOAT)/total_questions)*100 ELSE 0 END) 
                              FROM aptitude_submissions aps WHERE aps.student_id = u.id), 0) as avg_aptitude_score
                FROM users u
                LEFT JOIN users m ON u.mentor_id = m.id
                WHERE u.role = 'student'
            )
            SELECT * FROM student_stats
            ORDER BY (tasks_completed + problems_solved + aptitude_completed) DESC, avg_task_score DESC
        '''
        cursor.execute(query)
        rows = cursor.fetchall()
        print(f"Success! Found {len(rows)} students.")
        if rows:
            print("Top student:", rows[0]['name'], "Score:", rows[0]['avg_task_score'])
        
    except Exception as e:
        print(f"Query failed: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    test_query()
