from groq import Groq
from config import Config

def get_groq_client():
    """Get Groq client instance"""
    return Groq(api_key=Config.GROQ_API_KEY)

def evaluate_code(code, language, problem_description, expected_output=None, test_cases=None):
    """
    Evaluate code using Groq AI
    Returns: dict with score, status, feedback, and explanation
    """
    # Pre-check for empty/template code to prevent high scores for "pass"
    stripped_code = code.strip()
    normalized_code = "".join(code.split())
    
    # Default templates usually have specific signatures but little logic
    is_empty_or_pass = (
        len(stripped_code) < 20 or 
        (language == 'python' and 'pass' in stripped_code and len(stripped_code) < 100) or
        (language == 'c' and 'return 0' in stripped_code and len(stripped_code) < 100) or
        'Write your' in stripped_code and len(stripped_code) < 150
    )
    
    if is_empty_or_pass:
        return {
            'score': 0,
            'status': 'rejected',
            'feedback': 'Submission appears to be empty or just a template. Please implement the solution.',
            'correctness': 'No logic implemented - 0/40',
            'efficiency': 'N/A - 0/25',
            'code_style': 'Template only - 0/20',
            'best_practices': 'N/A - 0/15',
            'suggestions': 'Start by writing the core logic of the problem.'
        }

    try:
        client = get_groq_client()
        
        prompt = f"""You are an expert code evaluator for an educational platform. 
Evaluate the following {language} code submission for the given problem.

**Problem Description:**
{problem_description}

**Test Cases:**
{test_cases if test_cases else 'Not specified'}

**Expected Output:**
{expected_output if expected_output else 'Not specified'}

**Student's Code:**
```{language}
{code}
```

Please evaluate this code and provide:
1. **Score (0-100)**: Based on correctness, efficiency, code quality, and best practices.
   **CRITICAL REQUIREMENT:** If the code is empty, contains only comments, or just `pass`/`return 0` without implementing logic, the **Score MUST be 0**. Do not give partial marks for boilerplate.
2. **Status**: Either "accepted" or "rejected" (accepted if score >= 60)
3. **Feedback**: A brief message to show the student (2-3 sentences)
4. **Correctness**: One line about code correctness (score out of 40)
5. **Efficiency**: One line about time/space complexity (score out of 25)
6. **Code Style**: One line about code style and readability (score out of 20)
7. **Best Practices**: One line about best practices followed (score out of 15)
8. **Suggestions**: One line with improvement suggestions

Respond in the following JSON format only:
{{
    "score": <number>,
    "status": "<accepted/rejected>",
    "feedback": "<brief feedback for student>",
    "correctness": "<one line analysis with score like 'Correct implementation - 38/40'>",
    "efficiency": "<one line analysis with score like 'O(n) time complexity - 22/25'>",
    "code_style": "<one line analysis with score like 'Clean and readable - 18/20'>",
    "best_practices": "<one line analysis with score like 'Good naming conventions - 12/15'>",
    "suggestions": "<one line improvement suggestion>"
}}
"""
        
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You are an expert code evaluator. You are STRICT. Empty or boilerplate code gets 0 score. Always respond with valid JSON only, no additional text."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1000
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # Parse JSON response
        import json
        import re
        
        # Handle potential markdown code blocks
        if '```' in result_text:
            # Extract content between code blocks
            matches = re.findall(r'```(?:json)?\s*([\s\S]*?)```', result_text)
            if matches:
                result_text = matches[0].strip()
        
        # Clean control characters that can break JSON parsing
        result_text = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', result_text)
        
        # Try to find JSON object in the response
        json_match = re.search(r'\{[\s\S]*\}', result_text)
        if json_match:
            result_text = json_match.group()
        
        try:
            result = json.loads(result_text)
        except json.JSONDecodeError:
            # If JSON parsing fails, try to extract values manually
            score_match = re.search(r'"score"\s*:\s*(\d+)', result_text)
            score = int(score_match.group(1)) if score_match else 0  # Default to 0 on error if unsure
            
            return {
                'score': min(100, max(0, score)),
                'status': 'accepted' if score >= 60 else 'rejected',
                'feedback': 'Your solution has been evaluated.',
                'correctness': f'Code analysis completed - {int(score * 0.4)}/40',
                'efficiency': f'Efficiency evaluated - {int(score * 0.25)}/25',
                'code_style': f'Code style reviewed - {int(score * 0.2)}/20',
                'best_practices': f'Best practices checked - {int(score * 0.15)}/15',
                'suggestions': 'Review code for potential improvements.'
            }
        
        return {
            'score': min(100, max(0, int(result.get('score', 0)))),
            'status': 'accepted' if result.get('status', '').lower() == 'accepted' else 'rejected',
            'feedback': result.get('feedback', 'Evaluation completed.'),
            'correctness': result.get('correctness', 'Correctness evaluated'),
            'efficiency': result.get('efficiency', 'Efficiency evaluated'),
            'code_style': result.get('code_style', 'Code style evaluated'),
            'best_practices': result.get('best_practices', 'Best practices evaluated'),
            'suggestions': result.get('suggestions', 'No specific suggestions.')
        }
        
    except Exception as e:
        print(f"AI Evaluation Error: {str(e)}")
        return {
            'score': 0,
            'status': 'rejected',
            'feedback': f'AI evaluation error. Please try again.',
            'correctness': 'Unable to evaluate - 0/40',
            'efficiency': 'Unable to evaluate - 0/25',
            'code_style': 'Unable to evaluate - 0/20',
            'best_practices': 'Unable to evaluate - 0/15',
            'suggestions': 'Please try submitting again.'
        }

def evaluate_task_submission(content, task_description):
    """
    Evaluate task submission using Groq AI
    Returns: dict with score, status, feedback, and structured evaluation
    """
    try:
        client = get_groq_client()
        
        prompt = f"""You are an expert assignment evaluator for an educational platform.
Evaluate the following task submission.

**Task Description:**
{task_description}

**Student's Submission:**
{content}

Please evaluate this submission and provide:
1. **Score (0-100)**: Based on completeness, correctness, quality, and effort
2. **Status**: Either "accepted" or "rejected" (accepted if score >= 60)
3. **Feedback**: A brief message to show the student (2-3 sentences)
4. **Correctness**: One line about answer correctness (score out of 40)
5. **Efficiency**: One line about approach quality (score out of 25)
6. **Code Style**: One line about presentation and clarity (score out of 20)
7. **Best Practices**: One line about best practices followed (score out of 15)
8. **Suggestions**: One line with improvement suggestions

Respond in the following JSON format only:
{{
    "score": <number>,
    "status": "<accepted/rejected>",
    "feedback": "<brief feedback for student>",
    "correctness": "<one line analysis with score like 'Complete and accurate answer - 36/40'>",
    "efficiency": "<one line analysis with score like 'Clear approach - 20/25'>",
    "code_style": "<one line analysis with score like 'Well presented - 17/20'>",
    "best_practices": "<one line analysis with score like 'Good effort shown - 12/15'>",
    "suggestions": "<one line improvement suggestion>"
}}
"""
        
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You are an expert assignment evaluator. Always respond with valid JSON only, no additional text."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1000
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # Parse JSON response
        import json
        import re
        
        # Handle potential markdown code blocks
        if '```' in result_text:
            matches = re.findall(r'```(?:json)?\s*([\s\S]*?)```', result_text)
            if matches:
                result_text = matches[0].strip()
        
        # Clean control characters
        result_text = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', result_text)
        
        # Try to find JSON object
        json_match = re.search(r'\{[\s\S]*\}', result_text)
        if json_match:
            result_text = json_match.group()
        
        try:
            result = json.loads(result_text)
        except json.JSONDecodeError:
            score_match = re.search(r'"score"\s*:\s*(\d+)', result_text)
            score = int(score_match.group(1)) if score_match else 75
            
            return {
                'score': min(100, max(0, score)),
                'status': 'accepted' if score >= 60 else 'rejected',
                'feedback': 'Your submission has been evaluated.',
                'correctness': f'Analysis completed - {int(score * 0.4)}/40',
                'efficiency': f'Approach evaluated - {int(score * 0.25)}/25',
                'code_style': f'Presentation reviewed - {int(score * 0.2)}/20',
                'best_practices': f'Best practices checked - {int(score * 0.15)}/15',
                'suggestions': 'Review submission for potential improvements.'
            }
        
        return {
            'score': min(100, max(0, int(result.get('score', 0)))),
            'status': 'accepted' if result.get('status', '').lower() == 'accepted' else 'rejected',
            'feedback': result.get('feedback', 'Evaluation completed.'),
            'correctness': result.get('correctness', 'Correctness evaluated'),
            'efficiency': result.get('efficiency', 'Efficiency evaluated'),
            'code_style': result.get('code_style', 'Presentation evaluated'),
            'best_practices': result.get('best_practices', 'Best practices evaluated'),
            'suggestions': result.get('suggestions', 'No specific suggestions.')
        }
        
    except Exception as e:
        print(f"AI Evaluation Error: {str(e)}")
        return {
            'score': 0,
            'status': 'rejected',
            'feedback': f'AI evaluation error. Please try again.',
            'correctness': 'Unable to evaluate - 0/40',
            'efficiency': 'Unable to evaluate - 0/25',
            'code_style': 'Unable to evaluate - 0/20',
            'best_practices': 'Unable to evaluate - 0/15',
            'suggestions': 'Please try submitting again.'
        }

def get_code_hints(code, language, problem_description):
    """
    Get AI-powered hints for stuck students
    """
    if not Config.GROQ_API_KEY or Config.GROQ_API_KEY == 'your_groq_api_key_here':
        return "Hints are not available. Please configure your GROQ_API_KEY in the .env file to enable AI hints."
    
    try:
        client = get_groq_client()
        
        prompt = f"""You are a helpful coding tutor. A student is working on the following problem and seems stuck.

**Problem:**
{problem_description}

**Student's Current Code ({language}):**
```{language}
{code}
```

Provide 2 helpful hints without giving away the complete solution. 
Be encouraging and guide them towards the right approach.
Format your hints as numbered bullet points.
"""
        
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You are a helpful and encouraging coding tutor."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        error_msg = str(e)
        print(f"Hints Error: {error_msg}")
        if "api_key" in error_msg.lower() or "authentication" in error_msg.lower():
            return "API key error. Please check your GROQ_API_KEY in the .env file."
        elif "connection" in error_msg.lower() or "network" in error_msg.lower():
            return "Connection error. Please check your internet connection and try again."
        else:
            return f"Unable to generate hints: {error_msg}"

