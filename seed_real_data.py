
import sqlite3
from werkzeug.security import generate_password_hash

DATABASE_PATH = 'database.db'

# Data Structure: Mentor -> [Students]
DATA = {
    "HEMA PRIYA": ["PRABANJAN", "SANJEEV KUMAR", "NITHISH", "VENKATESH", "HARINI P (B SEC)", "THARANIYA", "HARINI P (A SEC)"],
    "RAKSHITA": ["ANUSHREE", "HEMACHANDRAN", "RAVIKANTH", "HARISH", "PRADEEP RAJ", "RHINDHIYA", "SHIVANI"],
    "BUMIKA": ["GANESH I", "DAKSHANAMOORTHY", "THEENASH", "SANGARADAS", "SRIVATSAN", "NARMADHA", "KAVITHA"],
    "KRISHNA KUMAR": ["AISWA MALAR", "HEMAJOTHI", "DEVISRI", "VAISHAL MALLU", "RAYYAN", "VISHNU PRASATH"],
    "SHYAAM KUMAR": ["MANOJ KUMAR", "ABISHEK BEHARA", "RAGUL", "GURALARASAN", "JAIDHAR", "SUBITSHA"],
    "HARESH G": ["ARUN SRINIVAS", "DAKSHA CHARAN", "PRAVEEN KUMAR", "ROHAN KUMAR", "THANUSH", "SIDARTH", "VISHWA P"],
    "KAVESH": ["ABDUL KALAM", "ABIEESHWAR", "AKILESH", "BHARANIDHARAN", "KARTHIKEYAN", "NAVANEETHAKRISHNAN", "RATHNA PRASAD"],
    "LOKESH": ["HEMESHWARAN", "MANIKANDAN", "MUGASH", "AL RAAFHATH", "DHIVYANAND", "LOKESHWAR", "VISHAL S"],
    
    # From Image 2
    "LAVANYA": ["MEENALOSHINI", "CHANDRA", "NITHYA SHRI B", "SIVARANJANI", "SRI AISHWARYA", "HARINI (REDO)", "HARINI A"],
    "DHINESHKUMAR G": ["AKSHAYA", "SUSHMIDHA M", "INDHUJA S", "MORDHEESH", "NITHYA SHRI V", "PRIYANKA", "KANIMOZHI"],
    "GOKULAN": ["PRATHEEB E", "PRIYAMADHAN", "SATHIYAN", "SUDHARSAN", "KARTHIK M", "HEMSHAKTHIRAM"],
    "SHARLI": ["DAMINI", "REYASH", "HARIJA", "PRAMILA", "SUSHMA", "ASWITTA"],
    "ABIRAMI": ["KARMUGILAN", "LALITHAMBIGA", "MOHANAPRIYA", "UTHRADEVI", "NAVEEN KUMAR", "GANESH DEEPAK", "VISHNU LAKSHMI"],
    "APARNAA": ["AMIRTHA BHANU", "DHIVYA", "HAFZA", "AGALYA", "HARIPRIYA", "SHIVANI", "KAVIYA P S"]
}

def generate_email(name, role, count=None):
    clean_name = name.lower().replace(" ", ".").replace("(", "").replace(")", "")
    suffix = f"{count}" if count else ""
    domain = "edufocal.com"
    return f"{clean_name}{suffix}@{domain}"

def seed_data():
    print("Connecting to database...")
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    print("Wiping existing users and submissions...")
    # Delete all users except we will re-create admin. Actually let's just wipe all.
    cursor.execute("DELETE FROM users")
    cursor.execute("DELETE FROM problem_submissions")
    cursor.execute("DELETE FROM task_submissions")
    
    # Reset sequences
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='users'")

    print("Creating System Admin...")
    admin_password = generate_password_hash("admin123")
    cursor.execute("INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
                  ("System Admin", "admin@eduplatform.com", admin_password, "admin"))
    
    # Track assigned emails to handle duplicates
    existing_emails = set()
    existing_emails.add("admin@eduplatform.com")
    
    first_mentor_id = None

    for mentor_name, students in DATA.items():
        # Create Mentor
        email = generate_email(mentor_name, "mentor")
        # Handle duplicate mentor names if any (unlikely here)
        if email in existing_emails:
            email = generate_email(mentor_name, "mentor", 2)
        existing_emails.add(email)
        
        password = generate_password_hash("password123")
        
        cursor.execute("INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
                      (mentor_name, email, password, "mentor"))
        mentor_id = cursor.lastrowid
        
        if first_mentor_id is None:
            first_mentor_id = mentor_id
            
        print(f"Created Mentor: {mentor_name} ({email})")
        
        # Create Students
        for student_name in students:
            s_email = generate_email(student_name, "student")
            count = 1
            while s_email in existing_emails:
                count += 1
                s_email = generate_email(student_name, "student", count)
            existing_emails.add(s_email)
            
            s_password = generate_password_hash("password123")
            
            cursor.execute("INSERT INTO users (name, email, password, role, mentor_id) VALUES (?, ?, ?, ?, ?)",
                          (student_name, s_email, s_password, "student", mentor_id))
            # print(f"  - Student: {student_name} ({s_email})")

    if first_mentor_id:
        print(f"Reassigning existing Problems/Tasks to first mentor (ID: {first_mentor_id})...")
        cursor.execute("UPDATE problems SET mentor_id = ?", (first_mentor_id,))
        cursor.execute("UPDATE tasks SET mentor_id = ?", (first_mentor_id,))

    conn.commit()
    conn.close()
    print("\nSUCCESS: Database populated with real data!")
    print("Default Student/Mentor Password: 'password123'")
    print("Admin Password: 'admin123'")

if __name__ == "__main__":
    seed_data()
