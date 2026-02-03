from flask import Flask, render_template, request, jsonify, redirect, url_for, session, send_from_directory
from flask_cors import CORS
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
import re
import secrets
from functools import wraps
import os
import json
from datetime import datetime

from config import Config
from database import get_db, init_db, seed_db
from ai_evaluator import evaluate_code, evaluate_task_submission
from plagiarism_checker import check_plagiarism
import json as json_lib

app = Flask(__name__, static_folder='static', template_folder='templates')
app.config.from_object(Config)
CORS(app)

# Ensure upload folder exists
os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)

# ============================================
# Authentication Decorators
# ============================================

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('login'))
            if session.get('role') not in roles:
                return redirect(url_for('unauthorized'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# ============================================
# Authentication Routes
# ============================================

@app.route('/')
def index():
    if 'user_id' in session:
        role = session.get('role')
        if role == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif role == 'mentor':
            return redirect(url_for('mentor_dashboard'))
        else:
            return redirect(url_for('student_dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        email = data.get('email')
        password = data.get('password')
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
        user = cursor.fetchone()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['email'] = user['email']
            session['role'] = user['role']
            session['mentor_id'] = user['mentor_id']
            
            # Log activity
            log_activity(user['id'], 'login', 'User logged in')
            
            if request.is_json:
                return jsonify({
                    'success': True,
                    'role': user['role'],
                    'redirect': url_for(f"{user['role']}_dashboard")
                })
            return redirect(url_for(f"{user['role']}_dashboard"))
        
        if request.is_json:
            return jsonify({'success': False, 'message': 'Invalid credentials'}), 401
        return render_template('login.html', error='Invalid credentials')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    if 'user_id' in session:
        log_activity(session['user_id'], 'logout', 'User logged out')
    session.clear()
    return redirect(url_for('login'))

@app.route('/unauthorized')
def unauthorized():
    return render_template('unauthorized.html')

# ============================================
# Student Routes
# ============================================

@app.route('/student/dashboard')
@role_required(['student'])
def student_dashboard():
    return render_template('student/dashboard.html')

@app.route('/student/tasks')
@role_required(['student'])
def student_tasks():
    return render_template('student/tasks.html')

@app.route('/student/assignments')
@role_required(['student'])
def student_assignments():
    return render_template('student/assignments.html')

@app.route('/student/submissions')
@role_required(['student'])
def student_submissions():
    return render_template('student/submissions.html')

# ============================================
# Mentor Routes
# ============================================

@app.route('/mentor/dashboard')
@role_required(['mentor'])
def mentor_dashboard():
    return render_template('mentor/dashboard.html')

@app.route('/mentor/tasks')
@role_required(['mentor', 'admin'])
def mentor_tasks():
    return render_template('mentor/tasks.html')

@app.route('/mentor/problems')
@role_required(['mentor', 'admin'])
def mentor_problems():
    return render_template('mentor/problems.html')

@app.route('/mentor/leaderboard')
@role_required(['mentor'])
def mentor_leaderboard():
    return render_template('mentor/leaderboard.html')

# ============================================
# Admin Routes
# ============================================

@app.route('/admin/dashboard')
@role_required(['admin'])
def admin_dashboard():
    return render_template('admin/dashboard.html')

@app.route('/admin/users')
@role_required(['admin'])
def admin_users():
    return render_template('admin/users.html')

@app.route('/admin/mentors')
@role_required(['admin'])
def admin_mentors():
    return render_template('admin/mentors.html')

@app.route('/admin/students')
@role_required(['admin'])
def admin_students():
    return render_template('admin/students.html')

@app.route('/admin/tasks')
@role_required(['admin'])
def admin_tasks():
    return render_template('admin/tasks.html')

@app.route('/admin/problems')
@role_required(['admin'])
def admin_problems():
    return render_template('admin/problems.html')

@app.route('/admin/aptitude')
@role_required(['admin'])
def admin_aptitude():
    return render_template('admin/aptitude.html')

# ============================================
# API Routes - Tasks
# ============================================

@app.route('/api/tasks', methods=['GET'])
@login_required
def get_tasks():
    conn = get_db()
    cursor = conn.cursor()
    
    if session['role'] == 'student':
        # Get tasks from student's mentor
        cursor.execute('''
            SELECT t.*, u.name as mentor_name,
                   (SELECT COUNT(*) FROM task_submissions ts WHERE ts.task_id = t.id AND ts.student_id = %s) as submitted
            FROM tasks t
            JOIN users u ON t.mentor_id = u.id
            WHERE (t.mentor_id = %s OR t.mentor_id IN (SELECT id FROM users WHERE role='admin')) AND t.is_active = 1
            ORDER BY t.created_at DESC
        ''', (session['user_id'], session['mentor_id']))
    elif session['role'] == 'mentor':
        # Get mentor's own tasks with submission count
        cursor.execute('''
            SELECT t.*, 
                   (SELECT COUNT(DISTINCT ts.student_id) FROM task_submissions ts WHERE ts.task_id = t.id) as submissions_count,
                   (SELECT COUNT(*) FROM users WHERE mentor_id = t.mentor_id AND role = 'student') as total_students
            FROM tasks t
            WHERE t.mentor_id = %s
            ORDER BY t.created_at DESC
        ''', (session['user_id'],))
    else:
        # Admin sees all tasks
        cursor.execute('''
            SELECT t.*, u.name as mentor_name,
                   (SELECT COUNT(DISTINCT ts.student_id) FROM task_submissions ts WHERE ts.task_id = t.id) as submissions_count,
                   (SELECT COUNT(*) FROM users WHERE role = 'student' AND (u.role = 'admin' OR mentor_id = u.id)) as total_students
            FROM tasks t
            JOIN users u ON t.mentor_id = u.id
            ORDER BY t.created_at DESC
        ''')
    
    tasks = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(tasks)

@app.route('/api/tasks', methods=['POST'])
@role_required(['mentor', 'admin'])
def create_task():
    data = request.get_json()
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO tasks (mentor_id, title, description, due_date)
        VALUES (%s, %s, %s, %s)
     RETURNING id''', (session['user_id'], data['title'], data['description'], data.get('due_date')))
    
    task_id = cursor.fetchone()['id']
    conn.commit()
    conn.close()
    
    log_activity(session['user_id'], 'create_task', f'Created task: {data["title"]}')
    
    return jsonify({'success': True, 'task_id': task_id})

@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
@role_required(['mentor', 'admin'])
def delete_task(task_id):
    conn = get_db()
    cursor = conn.cursor()
    
    # Verify ownership
    cursor.execute('SELECT mentor_id FROM tasks WHERE id = %s', (task_id,))
    task = cursor.fetchone()
    
    if not task or task['mentor_id'] != session['user_id']:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    cursor.execute('DELETE FROM tasks WHERE id = %s', (task_id,))
    cursor.execute('DELETE FROM task_submissions WHERE task_id = %s', (task_id,))
    conn.commit()
    conn.close()
    
    log_activity(session['user_id'], 'delete_task', f'Deleted task ID: {task_id}')
    
    return jsonify({'success': True})

@app.route('/api/tasks/<int:task_id>/toggle', methods=['POST'])
@role_required(['mentor', 'admin'])
def toggle_task(task_id):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT is_active, mentor_id FROM tasks WHERE id = %s', (task_id,))
    task = cursor.fetchone()
    
    if not task or task['mentor_id'] != session['user_id']:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    new_status = 0 if task['is_active'] else 1
    cursor.execute('UPDATE tasks SET is_active = %s WHERE id = %s', (new_status, task_id))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'is_active': new_status})

# ============================================
# API Routes - Problems
# ============================================

@app.route('/api/problems', methods=['GET'])
@login_required
def get_problems():
    conn = get_db()
    cursor = conn.cursor()
    
    if session['role'] == 'student':
        cursor.execute('''
            SELECT p.*, u.name as mentor_name,
                   (SELECT COUNT(*) FROM problem_submissions ps WHERE ps.problem_id = p.id AND ps.student_id = %s) as submitted
            FROM problems p
            JOIN users u ON p.mentor_id = u.id
            WHERE (p.mentor_id = %s OR p.mentor_id IN (SELECT id FROM users WHERE role='admin')) AND p.is_active = 1
            ORDER BY p.created_at DESC
        ''', (session['user_id'], session['mentor_id']))
    elif session['role'] == 'mentor':
        cursor.execute('''
            SELECT p.*, 
                   (SELECT COUNT(DISTINCT ps.student_id) FROM problem_submissions ps WHERE ps.problem_id = p.id) as submissions_count,
                   (SELECT COUNT(*) FROM users WHERE mentor_id = p.mentor_id AND role = 'student') as total_students
            FROM problems p
            WHERE p.mentor_id = %s
            ORDER BY p.created_at DESC
        ''', (session['user_id'],))
    else:
        cursor.execute('''
            SELECT p.*, u.name as mentor_name,
                   (SELECT COUNT(DISTINCT ps.student_id) FROM problem_submissions ps WHERE ps.problem_id = p.id) as submissions_count,
                   (SELECT COUNT(*) FROM users WHERE role = 'student' AND (u.role = 'admin' OR mentor_id = u.id)) as total_students
            FROM problems p
            JOIN users u ON p.mentor_id = u.id
            ORDER BY p.created_at DESC
        ''')
    
    problems = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(problems)

@app.route('/api/problems/<int:problem_id>', methods=['GET'])
@login_required
def get_problem(problem_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT p.*, u.name as mentor_name
        FROM problems p
        JOIN users u ON p.mentor_id = u.id
        WHERE p.id = %s
    ''', (problem_id,))
    problem = cursor.fetchone()
    conn.close()
    
    if problem:
        return jsonify(dict(problem))
    return jsonify({'error': 'Problem not found'}), 404

@app.route('/api/problems', methods=['POST'])
@role_required(['mentor', 'admin'])
def create_problem():
    data = request.get_json()
    
    # Process constraints (default to False if not provided)
    constraints = data.get('constraints', {})
    constraints_json = json_lib.dumps({
        'block_paste': constraints.get('block_paste', False),
        'disable_hints': constraints.get('disable_hints', False),
        'track_focus': constraints.get('track_focus', False)
    })
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO problems (mentor_id, title, description, problem_type, language, difficulty, test_cases, expected_output, constraints)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
     RETURNING id''', (
        session['user_id'],
        data['title'],
        data['description'],
        data['problem_type'],
        data.get('language', 'python'),
        data.get('difficulty', 'medium'),
        data.get('test_cases', ''),
        data.get('expected_output', ''),
        constraints_json
    ))
    
    problem_id = cursor.fetchone()['id']
    conn.commit()
    conn.close()
    
    log_activity(session['user_id'], 'create_problem', f'Created problem: {data["title"]}')
    
    return jsonify({'success': True, 'problem_id': problem_id})

@app.route('/api/problems/<int:problem_id>', methods=['DELETE'])
@role_required(['mentor', 'admin'])
def delete_problem(problem_id):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT mentor_id FROM problems WHERE id = %s', (problem_id,))
    problem = cursor.fetchone()
    
    if not problem or problem['mentor_id'] != session['user_id']:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    cursor.execute('DELETE FROM problems WHERE id = %s', (problem_id,))
    cursor.execute('DELETE FROM problem_submissions WHERE problem_id = %s', (problem_id,))
    conn.commit()
    conn.close()
    
    log_activity(session['user_id'], 'delete_problem', f'Deleted problem ID: {problem_id}')
    
    return jsonify({'success': True})

# ============================================
# API Routes - Submissions
# ============================================

@app.route('/api/task-submissions', methods=['GET'])
@login_required
def get_task_submissions():
    conn = get_db()
    cursor = conn.cursor()
    
    if session['role'] == 'student':
        cursor.execute('''
            SELECT ts.*, t.title as task_title, u.name as student_name
            FROM task_submissions ts
            JOIN tasks t ON ts.task_id = t.id
            JOIN users u ON ts.student_id = u.id
            WHERE ts.student_id = %s
            ORDER BY ts.submitted_at DESC
        ''', (session['user_id'],))
    elif session['role'] == 'mentor':
        cursor.execute('''
            SELECT ts.*, t.title as task_title, u.name as student_name
            FROM task_submissions ts
            JOIN tasks t ON ts.task_id = t.id
            JOIN users u ON ts.student_id = u.id
            WHERE u.mentor_id = %s
            ORDER BY ts.submitted_at DESC
        ''', (session['user_id'],))
    else:
        cursor.execute('''
            SELECT ts.*, t.title as task_title, u.name as student_name, m.name as mentor_name
            FROM task_submissions ts
            JOIN tasks t ON ts.task_id = t.id
            JOIN users u ON ts.student_id = u.id
            JOIN users m ON t.mentor_id = m.id
            ORDER BY ts.submitted_at DESC
        ''')
    
    submissions = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(submissions)

@app.route('/api/problem-submissions', methods=['GET'])
@login_required
def get_problem_submissions():
    conn = get_db()
    cursor = conn.cursor()
    
    if session['role'] == 'student':
        cursor.execute('''
            SELECT ps.*, p.title as problem_title, u.name as student_name,
                   source_u.name as plagiarism_source_name
            FROM problem_submissions ps
            JOIN problems p ON ps.problem_id = p.id
            JOIN users u ON ps.student_id = u.id
            LEFT JOIN users source_u ON ps.plagiarism_source_student_id = source_u.id
            WHERE ps.student_id = %s
            ORDER BY ps.submitted_at DESC
        ''', (session['user_id'],))
    elif session['role'] == 'mentor':
        cursor.execute('''
            SELECT ps.*, p.title as problem_title, u.name as student_name,
                   source_u.name as plagiarism_source_name
            FROM problem_submissions ps
            JOIN problems p ON ps.problem_id = p.id
            JOIN users u ON ps.student_id = u.id
            LEFT JOIN users source_u ON ps.plagiarism_source_student_id = source_u.id
            WHERE u.mentor_id = %s
            ORDER BY ps.submitted_at DESC
        ''', (session['user_id'],))
    else:
        cursor.execute('''
            SELECT ps.*, p.title as problem_title, u.name as student_name, m.name as mentor_name,
                   source_u.name as plagiarism_source_name
            FROM problem_submissions ps
            JOIN problems p ON ps.problem_id = p.id
            JOIN users u ON ps.student_id = u.id
            JOIN users m ON p.mentor_id = m.id
            LEFT JOIN users source_u ON ps.plagiarism_source_student_id = source_u.id
            ORDER BY ps.submitted_at DESC
        ''')
    
    submissions = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(submissions)

@app.route('/api/submit-task', methods=['POST'])
@role_required(['student'])
def submit_task():
    import json as json_lib
    task_id = request.form.get('task_id')
    submission_type = request.form.get('submission_type', 'editor')
    content = request.form.get('content', '')
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Get task details
    cursor.execute('SELECT * FROM tasks WHERE id = %s', (task_id,))
    task = cursor.fetchone()
    
    if not task:
        return jsonify({'success': False, 'message': 'Task not found'}), 404
    
    file_path = None
    
    # Handle file upload
    if submission_type == 'file' and 'file' in request.files:
        file = request.files['file']
        if file.filename:
            filename = secure_filename(f"{session['user_id']}_{task_id}_{file.filename}")
            file_path = os.path.join(Config.UPLOAD_FOLDER, filename)
            file.save(file_path)
            content = file.read().decode('utf-8', errors='ignore') if not file_path.endswith(('.pdf', '.doc', '.docx')) else f"[File: {filename}]"
    
    # AI Evaluation
    evaluation = evaluate_task_submission(content, task['description'])
    
    # Store structured evaluation as JSON
    structured_eval = {
        'correctness': evaluation.get('correctness', 'N/A'),
        'efficiency': evaluation.get('efficiency', 'N/A'),
        'code_style': evaluation.get('code_style', 'N/A'),
        'best_practices': evaluation.get('best_practices', 'N/A'),
        'suggestions': evaluation.get('suggestions', 'N/A')
    }
    
    cursor.execute('''
        INSERT INTO task_submissions (task_id, student_id, file_path, content, submission_type, status, score, ai_feedback, ai_explanation)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
     RETURNING id''', (
        task_id,
        session['user_id'],
        file_path,
        content,
        submission_type,
        evaluation['status'],
        evaluation['score'],
        evaluation['feedback'],
        json_lib.dumps(structured_eval)
    ))
    
    submission_id = cursor.fetchone()['id']
    conn.commit()
    conn.close()
    
    log_activity(session['user_id'], 'submit_task', f'Submitted task ID: {task_id}')
    
    return jsonify({
        'success': True,
        'submission_id': submission_id,
        'status': evaluation['status'],
        'score': evaluation['score'],
        'feedback': evaluation['feedback'],
        'correctness': evaluation.get('correctness', ''),
        'efficiency': evaluation.get('efficiency', ''),
        'code_style': evaluation.get('code_style', ''),
        'best_practices': evaluation.get('best_practices', ''),
        'suggestions': evaluation.get('suggestions', '')
    })

@app.route('/api/submit-problem', methods=['POST'])
@role_required(['student'])
def submit_problem():
    import json as json_lib
    data = request.get_json() if request.is_json else request.form
    problem_id = data.get('problem_id')
    code = data.get('code', '')
    language = data.get('language', 'python')
    submission_type = data.get('submission_type', 'editor')
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Get problem details
    cursor.execute('SELECT * FROM problems WHERE id = %s', (problem_id,))
    problem = cursor.fetchone()
    
    if not problem:
        return jsonify({'success': False, 'message': 'Problem not found'}), 404
    
    # Check for Plagiarism
    is_plagiarized, similarity, source_student_id = check_plagiarism(code, problem_id, session['user_id'], cursor)
    
    focus_lost_count = data.get('focus_lost_count', 0)
    paste_attempts = data.get('paste_attempts', 0)
    
    if is_plagiarized:
        evaluation = {
            'score': 0,
            'status': 'rejected',
            'feedback': f"Plagiarism detected! Your code is {int(similarity*100)}% similar to another student's submission.",
            'correctness': 'Plagiarism Detected',
            'efficiency': 'N/A',
            'code_style': 'N/A',
            'best_practices': 'Do not copy code.',
            'suggestions': 'Please write your own solution.'
        }
    elif focus_lost_count > 2 or paste_attempts > 0:
        # Strict Violation Policy: >2 Focus drops or ANY paste attempt = Reject
        evaluation = {
            'score': 0,
            'status': 'rejected',
            'feedback': f"Submission rejected due to Exam Violations. Focus lost: {focus_lost_count} times, Paste attempts: {paste_attempts}.",
            'correctness': 'Exam Violation',
            'efficiency': 'N/A',
            'code_style': 'N/A',
            'best_practices': 'Follow exam rules.',
            'suggestions': 'Maintain focus and typing manually is required.'
        }
    else:
        # AI Evaluation
        evaluation = evaluate_code(
            code,
            language,
            problem['description'],
            problem['expected_output'],
            problem['test_cases']
        )
    
    # Store structured evaluation as JSON
    structured_eval = {
        'correctness': evaluation.get('correctness', 'N/A'),
        'efficiency': evaluation.get('efficiency', 'N/A'),
        'code_style': evaluation.get('code_style', 'N/A'),
        'best_practices': evaluation.get('best_practices', 'N/A'),
        'suggestions': evaluation.get('suggestions', 'N/A')
    }
    
    cursor.execute('''
        INSERT INTO problem_submissions (problem_id, student_id, code, language, submission_type, status, score, ai_feedback, ai_explanation, is_plagiarized, plagiarism_score, plagiarism_source_student_id, focus_lost_count, paste_attempts)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
     RETURNING id''', (
        problem_id,
        session['user_id'],
        code,
        language,
        submission_type,
        evaluation['status'],
        evaluation['score'],
        evaluation['feedback'],
        json_lib.dumps(structured_eval),
        is_plagiarized,
        similarity if is_plagiarized else 0.0,
        source_student_id if is_plagiarized else None,
        focus_lost_count,
        paste_attempts
    ))
    
    submission_id = cursor.fetchone()['id']
    conn.commit()
    conn.close()
    
    log_activity(session['user_id'], 'submit_problem', f'Submitted problem ID: {problem_id}')
    
    return jsonify({
        'success': True,
        'submission_id': submission_id,
        'status': evaluation['status'],
        'score': evaluation['score'],
        'feedback': evaluation['feedback'],
        'correctness': evaluation.get('correctness', ''),
        'efficiency': evaluation.get('efficiency', ''),
        'code_style': evaluation.get('code_style', ''),
        'best_practices': evaluation.get('best_practices', ''),
        'suggestions': evaluation.get('suggestions', '')
    })

@app.route('/api/submissions/<string:type>/<int:submission_id>', methods=['DELETE'])
@role_required(['student'])
def delete_submission(type, submission_id):
    conn = get_db()
    cursor = conn.cursor()
    
    table = 'task_submissions' if type == 'task' else 'problem_submissions'
    
    cursor.execute(f'SELECT student_id FROM {table} WHERE id = %s', (submission_id,))
    submission = cursor.fetchone()
    
    if not submission or submission['student_id'] != session['user_id']:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    cursor.execute(f'DELETE FROM {table} WHERE id = %s', (submission_id,))
    conn.commit()
    conn.close()
    
    log_activity(session['user_id'], 'delete_submission', f'Deleted {type} submission ID: {submission_id}')
    
    return jsonify({'success': True})

# ============================================
# API Routes - Hints
# ============================================

@app.route('/api/hints', methods=['POST'])
@role_required(['student'])
def get_hints():
    data = request.get_json()
    problem_id = data.get('problem_id')
    code = data.get('code', '')
    language = data.get('language', 'python')  # Get language from frontend
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM problems WHERE id = %s', (problem_id,))
    problem = cursor.fetchone()
    conn.close()
    
    if not problem:
        return jsonify({'success': False, 'message': 'Problem not found'}), 404
    
    # Use language from request if provided, otherwise fall back to problem's language
    hint_language = language if language else problem['language']
    hints = get_code_hints(code, hint_language, problem['description'])
    
    return jsonify({'success': True, 'hints': hints})

# ============================================
# API Routes - Users (Admin)
# ============================================

@app.route('/api/users', methods=['GET'])
@role_required(['admin'])
def get_users():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT u.id, u.email, u.name, u.role, u.mentor_id, u.created_at,
               m.name as mentor_name
        FROM users u
        LEFT JOIN users m ON u.mentor_id = m.id
        ORDER BY u.role, u.name
    ''')
    users = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(users)

@app.route('/api/users', methods=['POST'])
@role_required(['admin'])
def create_user():
    data = request.get_json()
    
    conn = get_db()
    cursor = conn.cursor()
    
    hashed_password = generate_password_hash(data['password'])
    
    try:
        cursor.execute('''
            INSERT INTO users (email, password, name, role, mentor_id)
            VALUES (%s, %s, %s, %s, %s)
         RETURNING id''', (
            data['email'],
            hashed_password,
            data['name'],
            data['role'],
            data.get('mentor_id')
        ))
        
        user_id = cursor.fetchone()['id']
        conn.commit()
        conn.close()
        
        log_activity(session['user_id'], 'create_user', f'Created user: {data["email"]}')
        
        return jsonify({'success': True, 'user_id': user_id})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
@role_required(['admin'])
def delete_user(user_id):
    if user_id == session['user_id']:
        return jsonify({'success': False, 'message': 'Cannot delete yourself'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM users WHERE id = %s', (user_id,))
    conn.commit()
    conn.close()
    
    log_activity(session['user_id'], 'delete_user', f'Deleted user ID: {user_id}')
    
    return jsonify({'success': True})

@app.route('/api/mentors', methods=['GET'])
@login_required
def get_mentors():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, name, email
        FROM users
        WHERE role = 'mentor'
        ORDER BY name
    ''')
    mentors = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(mentors)

@app.route('/api/mentor-students', methods=['GET'])
@role_required(['admin', 'mentor'])
def get_mentor_students():
    conn = get_db()
    cursor = conn.cursor()
    
    if session['role'] == 'mentor':
        cursor.execute('''
            SELECT id, name, email, created_at
            FROM users
            WHERE mentor_id = %s AND role = 'student'
            ORDER BY name
        ''', (session['user_id'],))
    else:
        cursor.execute('''
            SELECT u.id, u.name, u.email, u.created_at, m.name as mentor_name, m.id as mentor_id
            FROM users u
            LEFT JOIN users m ON u.mentor_id = m.id
            WHERE u.role = 'student'
            ORDER BY m.name, u.name
        ''')
    
    students = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(students)

# ============================================
@app.route('/api/skills', methods=['GET'])
@login_required
def get_skills_distribution():
    conn = get_db()
    cursor = conn.cursor()
    
    # Select AI explanations
    if session['role'] == 'student':
        cursor.execute("SELECT ai_explanation FROM problem_submissions WHERE student_id = %s AND ai_explanation IS NOT NULL", (session['user_id'],))
    elif session['role'] == 'mentor':
        cursor.execute('''
            SELECT ps.ai_explanation 
            FROM problem_submissions ps
            JOIN problems p ON ps.problem_id = p.id
            WHERE p.mentor_id = %s AND ps.ai_explanation IS NOT NULL
        ''', (session['user_id'],))
    else:
        cursor.execute("SELECT ai_explanation FROM problem_submissions WHERE ai_explanation IS NOT NULL")
        
    rows = cursor.fetchall()
    conn.close()
    
    metrics = {
        'correctness': {'total': 0, 'count': 0, 'max': 40},
        'efficiency': {'total': 0, 'count': 0, 'max': 25},
        'code_style': {'total': 0, 'count': 0, 'max': 20},
        'best_practices': {'total': 0, 'count': 0, 'max': 15}
    }
    
    for row in rows:
        try:
            data = json_lib.loads(row['ai_explanation'])
            
            for key in metrics:
                text = data.get(key, '')
                # Extract number/number e.g. "35/40"
                match = re.search(r'([-+]%s\d*\.%s\d+)/(\d+)', text)
                if match:
                    val = float(match.group(1))
                    metrics[key]['total'] += val
                    metrics[key]['count'] += 1
        except:
            continue
            
    # Calculate percentages
    final_scores = {}
    for key, data in metrics.items():
        if data['count'] > 0:
            avg_raw = data['total'] / data['count']
            percent = (avg_raw / data['max']) * 100
            final_scores[key] = round(percent, 1)
        else:
            final_scores[key] = 0
            
    return jsonify(final_scores)



# ============================================

@app.route('/api/leaderboard/students', methods=['GET'])
@login_required
def student_leaderboard():
    conn = get_db()
    cursor = conn.cursor()
    
    if session['role'] == 'mentor':
        mentor_id = session['user_id']
    elif session['role'] == 'student':
        mentor_id = session['mentor_id']
    else:
        mentor_id = None
    
    # In PostgreSQL, we can't easily use aliases in the ORDER BY if they are subqueries.
    # Using a CTE (Common Table Expression) to make it clean and portable.
    base_query = '''
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
    '''
    
    mentor_id = request.args.get('mentor_id')
    
    if session['role'] == 'mentor' and not mentor_id:
        mentor_id = session['user_id']
    elif session['role'] == 'student' and not mentor_id:
        # Students see everyone or just their group? Usually global is better for competition.
        # But if the user wants "mirroring mentor view", maybe group?
        # I'll keep it global for students unless specified.
        pass

    if mentor_id:
        cursor.execute(base_query + " WHERE mentor_id = %s ORDER BY (tasks_completed + problems_solved + aptitude_completed) DESC, avg_task_score DESC", (mentor_id,))
    else:
        cursor.execute(base_query + " ORDER BY (tasks_completed + problems_solved + aptitude_completed) DESC, avg_task_score DESC")
    
    leaderboard = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(leaderboard)

@app.route('/api/leaderboard/mentors', methods=['GET'])
@role_required(['admin'])
def get_mentor_leaderboard_api():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        WITH mentor_stats AS (
            SELECT 
                u.id, u.name, u.email,
                (SELECT COUNT(*) FROM tasks t WHERE t.mentor_id = u.id) as total_tasks,
                (SELECT COUNT(*) FROM problems p WHERE p.mentor_id = u.id) as total_problems,
                (SELECT COUNT(*) FROM users s WHERE s.mentor_id = u.id AND s.role = 'student') as total_students,
                (SELECT COUNT(*) FROM task_submissions ts 
                 JOIN tasks t ON ts.task_id = t.id 
                 WHERE t.mentor_id = u.id AND ts.status = 'accepted') as completed_tasks,
                (SELECT COUNT(*) FROM problem_submissions ps 
                 JOIN problems p ON ps.problem_id = p.id 
                 WHERE p.mentor_id = u.id AND ps.status = 'accepted') as solved_problems
            FROM users u
            WHERE u.role = 'mentor'
        )
        SELECT * FROM mentor_stats
        ORDER BY (total_tasks + total_problems) DESC
    ''')
    
    leaderboard = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(leaderboard)

# ============================================
# API Routes - Statistics
# ============================================

@app.route('/api/stats', methods=['GET'])
@login_required
def get_stats():
    conn = get_db()
    cursor = conn.cursor()
    
    stats = {}
    
    if session['role'] == 'student':
        student_id = session['user_id']
        
        cursor.execute('SELECT COUNT(*) FROM tasks WHERE mentor_id = %s AND is_active = 1', (session['mentor_id'],))
        stats['total_tasks'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM task_submissions WHERE student_id = %s AND status = 'accepted'", (student_id,))
        stats['completed_tasks'] = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM problems WHERE mentor_id = %s AND is_active = 1', (session['mentor_id'],))
        stats['total_problems'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM problem_submissions WHERE student_id = %s AND status = 'accepted'", (student_id,))
        stats['solved_problems'] = cursor.fetchone()[0]
        
        cursor.execute('SELECT AVG(score) FROM task_submissions WHERE student_id = %s', (student_id,))
        stats['avg_task_score'] = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT AVG(score) FROM problem_submissions WHERE student_id = %s', (student_id,))
        stats['avg_problem_score'] = cursor.fetchone()[0] or 0
        
    elif session['role'] == 'mentor':
        mentor_id = session['user_id']
        
        cursor.execute('SELECT COUNT(*) FROM tasks WHERE mentor_id = %s', (mentor_id,))
        stats['total_tasks'] = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM problems WHERE mentor_id = %s', (mentor_id,))
        stats['total_problems'] = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM users WHERE mentor_id = %s AND role = "student"', (mentor_id,))
        stats['total_students'] = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT COUNT(*) FROM task_submissions ts
            JOIN tasks t ON ts.task_id = t.id
            WHERE t.mentor_id = %s
        ''', (mentor_id,))
        stats['total_task_submissions'] = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT COUNT(*) FROM problem_submissions ps
            JOIN problems p ON ps.problem_id = p.id
            WHERE p.mentor_id = %s
        ''', (mentor_id,))
        stats['total_problem_submissions'] = cursor.fetchone()[0]
        
    else:  # admin
        cursor.execute('SELECT COUNT(*) FROM users WHERE role = "mentor"')
        stats['total_mentors'] = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM users WHERE role = "student"')
        stats['total_students'] = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM tasks')
        stats['total_tasks'] = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM problems')
        stats['total_problems'] = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM task_submissions')
        stats['total_task_submissions'] = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM problem_submissions')
        stats['total_problem_submissions'] = cursor.fetchone()[0]
    
    conn.close()
    return jsonify(stats)

# ============================================
# API Routes - Activity Logs
# ============================================

@app.route('/api/activity-logs', methods=['GET'])
@role_required(['admin'])
def get_activity_logs():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT al.*, u.name as user_name, u.role as user_role
        FROM activity_logs al
        JOIN users u ON al.user_id = u.id
        ORDER BY al.created_at DESC
        LIMIT 100
    ''')
    logs = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(logs)

def log_activity(user_id, action, details):
    """Log user activity"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO activity_logs (user_id, action, details)
            VALUES (%s, %s, %s)
         RETURNING id''', (user_id, action, details))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error logging activity: {e}")

# ============================================
# Static Files
# ============================================

@app.route('/uploads/<path:filename>')
@login_required
def uploaded_file(filename):
    return send_from_directory(Config.UPLOAD_FOLDER, filename)

# ============================================
# Error Handlers
# ============================================

@app.errorhandler(404)
# ============================================
# Aptitude Routes
# ============================================

@app.route('/mentor/aptitude')
@role_required(['mentor', 'admin'])
def mentor_aptitude():
    return render_template('mentor/aptitude.html')

@app.route('/student/aptitude')
@role_required(['student'])
def student_aptitude():
    return render_template('student/aptitude.html')

# API Routes - Aptitude

@app.route('/api/aptitude', methods=['GET'])
@login_required
def get_aptitude_tests():
    conn = get_db()
    cursor = conn.cursor()
    
    if session['role'] == 'student':
        # Get active tests from mentor or admin (filter by end_time)
        cursor.execute('''
            SELECT t.id, t.title, t.description, t.duration, t.created_at, t.end_time, t.attempt_limit, u.name as mentor_name,
                   (SELECT MAX(score) FROM aptitude_submissions s WHERE s.test_id = t.id AND s.student_id = %s) as my_score,
                   (SELECT COUNT(*) FROM aptitude_submissions s WHERE s.test_id = t.id AND s.student_id = %s) as attempts_taken
            FROM aptitude_tests t
            JOIN users u ON t.mentor_id = u.id
            WHERE (t.mentor_id = %s OR t.mentor_id IN (SELECT id FROM users WHERE role='admin')) 
                  AND t.is_active = 1
                  AND (t.end_time IS NULL OR t.end_time > CURRENT_TIMESTAMP)
            ORDER BY t.created_at DESC
        ''', (session['user_id'], session['user_id'], session['mentor_id']))
    elif session['role'] == 'admin':
        # Admin sees all tests
        cursor.execute('''
            SELECT t.*, u.name as mentor_name,
                   (SELECT COUNT(*) FROM aptitude_submissions s WHERE s.test_id = t.id) as submissions_count,
                   (SELECT COUNT(*) FROM users WHERE role = 'student' AND (u.role = 'admin' OR mentor_id = u.id)) as total_students
            FROM aptitude_tests t
            JOIN users u ON t.mentor_id = u.id
            ORDER BY t.created_at DESC
        ''')
    else:
        # Mentor sees their tests
        cursor.execute('''
            SELECT t.*, 
                   (SELECT COUNT(*) FROM aptitude_submissions s WHERE s.test_id = t.id) as submissions_count,
                   (SELECT COUNT(*) FROM users WHERE mentor_id = t.mentor_id AND role = 'student') as total_students
            FROM aptitude_tests t
            WHERE t.mentor_id = %s
            ORDER BY t.created_at DESC
        ''', (session['user_id'],))
        
    tests = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(tests)

@app.route('/api/aptitude', methods=['POST'])
@role_required(['mentor', 'admin'])
def create_aptitude_test():
    data = request.get_json()
    conn = get_db()
    cursor = conn.cursor()
    
    end_time = data.get('end_time')  # Optional: YYYY-MM-DD HH:MM format
    attempt_limit = data.get('attempt_limit') 
    
    cursor.execute('''
        INSERT INTO aptitude_tests (mentor_id, title, description, duration, questions, end_time, attempt_limit)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
     RETURNING id''', (session['user_id'], data['title'], data['description'], data['duration'], json_lib.dumps(data['questions']), end_time, attempt_limit))
    
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/aptitude/<int:test_id>', methods=['GET'])
@login_required
def get_aptitude_test(test_id):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM aptitude_tests WHERE id = %s', (test_id,))
    test = cursor.fetchone()
    conn.close()
    
    if not test:
        return jsonify({'error': 'Test not found'}), 404
        
    test_dict = dict(test)
    questions = json_lib.loads(test_dict['questions'])
    
    if session['role'] == 'student':
        # Check attempt limit
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM aptitude_submissions WHERE test_id = %s AND student_id = %s', (test_id, session['user_id']))
        attempts_taken = cursor.fetchone()[0]
        conn.close()

        if test_dict.get('attempt_limit') and attempts_taken >= test_dict['attempt_limit']:
             return jsonify({'error': 'Maximum attempts reached'}), 403

        # Remove correct answer from payload
        for q in questions:
            if 'correct' in q: del q['correct']
    
    test_dict['questions'] = questions
    return jsonify(test_dict)

@app.route('/api/aptitude/<int:test_id>', methods=['DELETE'])
@role_required(['mentor', 'admin'])
def delete_aptitude_test(test_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM aptitude_tests WHERE id=%s', (test_id,))
    cursor.execute('DELETE FROM aptitude_submissions WHERE test_id=%s', (test_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/aptitude/<int:test_id>/submit', methods=['POST'])
@role_required(['student'])
def submit_aptitude(test_id):
    data = request.get_json()
    student_answers = data.get('answers', {}) 
    focus_lost_count = data.get('focus_lost_count', 0)
    paste_attempts = data.get('paste_attempts', 0)
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT questions FROM aptitude_tests WHERE id = %s', (test_id,))
    row = cursor.fetchone()
    if not row: return jsonify({'error': 'Test not found'}), 404
    
    questions = json_lib.loads(row['questions'])
    score = 0
    total = len(questions)
    
    for idx, q in enumerate(questions):
        student_ans = student_answers.get(str(idx))
        if student_ans is not None and int(student_ans) == int(q['correct']):
            score += 1
            
    # Check existing submission%s Allow multiple%s Assuming single for now or overwrite.
    # User didn't specify. I'll allow overwrite or just insert new. Insert new is safer for history.
    cursor.execute('''
        INSERT INTO aptitude_submissions (student_id, test_id, score, total_questions, answers, focus_lost_count, paste_attempts)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
     RETURNING id''', (session['user_id'], test_id, score, total, json_lib.dumps(student_answers), focus_lost_count, paste_attempts))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'score': score, 'total': total})

@app.route('/api/aptitude-submissions', methods=['GET'])
@role_required(['student'])
def get_aptitude_submissions_list():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT s.*, t.title as test_title, s.total_questions as q_count
        FROM aptitude_submissions s
        JOIN aptitude_tests t ON s.test_id = t.id
        WHERE s.student_id = %s
        ORDER BY s.submitted_at DESC
    ''', (session['user_id'],))
    submissions = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(submissions)

@app.route('/api/stats/dashboard', methods=['GET'])
@login_required
def get_dashboard_stats():
    conn = get_db()
    cursor = conn.cursor()
    stats = {}
    
    role = session['role']
    user_id = session['user_id']
    
    if role == 'student':
        cursor.execute("SELECT COUNT(*) FROM task_submissions WHERE student_id = %s", (user_id,))
        stats['tasks_submitted'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM problem_submissions WHERE student_id = %s", (user_id,))
        stats['problems_solved'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM aptitude_submissions WHERE student_id = %s", (user_id,))
        stats['aptitude_taken'] = cursor.fetchone()[0]
        
    elif role == 'mentor':
        cursor.execute("SELECT COUNT(*) FROM tasks WHERE mentor_id = %s", (user_id,))
        stats['tasks_created'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM problems WHERE mentor_id = %s", (user_id,))
        stats['problems_created'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM aptitude_tests WHERE mentor_id = %s", (user_id,))
        stats['aptitude_created'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE mentor_id = %s AND role = 'student'", (user_id,))
        stats['total_students'] = cursor.fetchone()[0]
        
        # Calculate actual total submissions for mentor's students
        cursor.execute('''
            SELECT COUNT(*) FROM task_submissions ts 
            JOIN users u ON ts.student_id = u.id 
            WHERE u.mentor_id = %s
        ''', (user_id,))
        task_subs = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT COUNT(*) FROM problem_submissions ps 
            JOIN users u ON ps.student_id = u.id 
            WHERE u.mentor_id = %s
        ''', (user_id,))
        prob_subs = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT COUNT(*) FROM aptitude_submissions aps 
            JOIN users u ON aps.student_id = u.id 
            WHERE u.mentor_id = %s
        ''', (user_id,))
        apt_subs = cursor.fetchone()[0]
        
        stats['total_submissions'] = task_subs + prob_subs + apt_subs
        
    elif role == 'admin':
        cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'student'")
        stats['total_students'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'mentor'")
        stats['total_mentors'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM tasks")
        stats['total_tasks'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM problems")
        stats['total_problems'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM aptitude_tests")
        stats['total_aptitude_tests'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM task_submissions")
        task_subs = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM problem_submissions")
        prob_subs = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM aptitude_submissions")
        apt_subs = cursor.fetchone()[0]
        
        stats['total_submissions'] = task_subs + prob_subs + apt_subs
        stats['total_task_submissions'] = task_subs
        stats['total_problem_submissions'] = prob_subs
        stats['total_aptitude_submissions'] = apt_subs

    conn.close()
    return jsonify(stats)

@app.route('/api/aptitude-submissions/all', methods=['GET'])
@role_required(['mentor', 'admin'])
def get_all_aptitude_submissions():
    conn = get_db()
    cursor = conn.cursor()
    
    if session['role'] == 'mentor':
        cursor.execute('''
            SELECT s.*, t.title as test_title, u.name as student_name
            FROM aptitude_submissions s
            JOIN aptitude_tests t ON s.test_id = t.id
            JOIN users u ON s.student_id = u.id
            WHERE u.mentor_id = %s
            ORDER BY s.submitted_at DESC
        ''', (session['user_id'],))
    else: # Admin
        cursor.execute('''
            SELECT s.*, t.title as test_title, u.name as student_name
            FROM aptitude_submissions s
            JOIN aptitude_tests t ON s.test_id = t.id
            JOIN users u ON s.student_id = u.id
            ORDER BY s.submitted_at DESC
        ''')
        
    submissions = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(submissions)

@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500

# ============================================
# Main
# ============================================

if __name__ == '__main__':
    init_db()
    seed_db()
    app.run(debug=True, port=5000)