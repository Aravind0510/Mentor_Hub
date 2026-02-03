
import difflib
import re

def normalize_code(code):
    """
    Normalize code to reduce false negatives from formatting changes.
    - Removes whitespace
    - Removes comments (basic)
    - Lowercases everything
    """
    # Remove single line comments (python style #)
    code = re.sub(r'#.*', '', code)
    # Remove single line comments (C/Java style //)
    code = re.sub(r'//.*', '', code)
    # Remove whitespace
    code = ''.join(code.split())
    return code.lower()

def check_plagiarism(new_code, problem_id, student_id, cursor):
    """
    Check if the new code is plagiarized from existing submissions.
    Returns: (is_plagiarized, max_similarity, source_student_id)
    """
    threshold = 0.85  # 85% similarity threshold
    
    # Get all previous accepted/rejected (but not from same student) submissions for this problem
    cursor.execute('''
        SELECT student_id, code 
        FROM problem_submissions 
        WHERE problem_id = %s AND student_id != %s AND code IS NOT NULL
    ''', (problem_id, student_id))
    
    previous_submissions = cursor.fetchall()
    
    normalized_new_code = normalize_code(new_code)
    
    if len(normalized_new_code) < 20: # Skip very short snippets
        return False, 0.0, None

    max_similarity = 0.0
    source_student_id = None
    
    # Check against all previous submissions
    for prev_student_id, prev_code in previous_submissions:
        if not prev_code:
            continue
            
        normalized_prev_code = normalize_code(prev_code)
        
        # Calculate similarity ratio
        matcher = difflib.SequenceMatcher(None, normalized_new_code, normalized_prev_code)
        similarity = matcher.ratio()
        
        if similarity > max_similarity:
            max_similarity = similarity
            source_student_id = prev_student_id
            
    is_plagiarized = max_similarity >= threshold
    
    return is_plagiarized, max_similarity, source_student_id
