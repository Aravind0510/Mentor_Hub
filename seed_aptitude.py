
import sqlite3
import json
from datetime import datetime, timedelta
from config import Config

def seed_aptitude_test():
    print("Seeding Aptitude Test with 20 questions...")
    
    conn = sqlite3.connect(Config.DATABASE_PATH)
    cursor = conn.cursor()
    
    # Get Admin user ID
    cursor.execute("SELECT id FROM users WHERE role='admin' LIMIT 1")
    admin = cursor.fetchone()
    if not admin:
        print("No admin found! Creating test under first mentor.")
        cursor.execute("SELECT id FROM users WHERE role='mentor' LIMIT 1")
        admin = cursor.fetchone()
    
    admin_id = admin[0]
    
    # 20 Aptitude Questions
    questions = [
        # CLOCKS (5 questions)
        {
            "text": "At what time between 3 and 4 o'clock are the hands of a clock together?",
            "options": ["3:16:22", "3:16:52", "3:15:00", "3:14:32"],
            "correct": 0
        },
        {
            "text": "What is the angle between the minute and hour hand at 3:30?",
            "options": ["75°", "90°", "105°", "60°"],
            "correct": 0
        },
        {
            "text": "How many times do the hands of a clock coincide in 24 hours?",
            "options": ["24", "22", "20", "21"],
            "correct": 1
        },
        {
            "text": "At what angle the hands of a clock are inclined at 15 minutes past 5?",
            "options": ["72.5°", "64°", "67.5°", "58.5°"],
            "correct": 2
        },
        {
            "text": "A clock shows 8:00. What is the angle between the hour and minute hands?",
            "options": ["120°", "150°", "240°", "60°"],
            "correct": 0
        },
        
        # NUMBER SYSTEM (5 questions)
        {
            "text": "What is the unit digit of 7^95?",
            "options": ["7", "9", "3", "1"],
            "correct": 2
        },
        {
            "text": "The sum of first 50 natural numbers is:",
            "options": ["1275", "1225", "1250", "1300"],
            "correct": 0
        },
        {
            "text": "Find the largest 4-digit number exactly divisible by 88.",
            "options": ["9944", "9768", "9988", "9900"],
            "correct": 0
        },
        {
            "text": "What is the remainder when 2^256 is divided by 17?",
            "options": ["1", "2", "16", "0"],
            "correct": 0
        },
        {
            "text": "How many prime numbers are there between 1 and 50?",
            "options": ["15", "16", "14", "13"],
            "correct": 0
        },
        
        # PERCENTAGES (3 questions)
        {
            "text": "If 20% of a number is 80, what is 40% of the same number?",
            "options": ["160", "200", "120", "140"],
            "correct": 0
        },
        {
            "text": "A shopkeeper sells an item at 25% profit. If the cost price is ₹400, what is the selling price?",
            "options": ["₹500", "₹450", "₹525", "₹475"],
            "correct": 0
        },
        {
            "text": "The price of an article was increased by 20% and then decreased by 20%. The net change is:",
            "options": ["No change", "4% decrease", "4% increase", "2% decrease"],
            "correct": 1
        },
        
        # PROFIT & LOSS (2 questions)
        {
            "text": "A man buys a TV for ₹10,000 and sells it at 10% loss. What is the selling price?",
            "options": ["₹9,000", "₹9,500", "₹8,500", "₹9,100"],
            "correct": 0
        },
        {
            "text": "If selling price is ₹96 and profit is 20%, what is the cost price?",
            "options": ["₹80", "₹76", "₹84", "₹72"],
            "correct": 0
        },
        
        # TIME & WORK (2 questions)
        {
            "text": "A can do a work in 15 days, B can do it in 10 days. Together they will complete it in:",
            "options": ["5 days", "6 days", "7 days", "8 days"],
            "correct": 1
        },
        {
            "text": "If 5 men can do a work in 20 days, how many days will 10 men take?",
            "options": ["10 days", "15 days", "5 days", "25 days"],
            "correct": 0
        },
        
        # AVERAGES (2 questions)
        {
            "text": "The average of 5 numbers is 20. If one number is excluded, the average becomes 18. The excluded number is:",
            "options": ["28", "24", "30", "26"],
            "correct": 0
        },
        {
            "text": "Average age of 10 students is 15 years. If teacher's age is included, average becomes 17. Teacher's age is:",
            "options": ["37 years", "35 years", "40 years", "32 years"],
            "correct": 0
        },
        
        # SIMPLE INTEREST (1 question)
        {
            "text": "Simple interest on ₹5000 at 8% per annum for 2 years is:",
            "options": ["₹800", "₹850", "₹900", "₹750"],
            "correct": 0
        }
    ]
    
    # Set end time to 24 hours from now
    end_time = (datetime.now() + timedelta(hours=24)).strftime('%Y-%m-%d %H:%M')
    
    cursor.execute('''
        INSERT INTO aptitude_tests (mentor_id, title, description, duration, questions, is_active, end_time)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        admin_id,
        "General Aptitude Test - Clocks, Numbers & More",
        "20 questions covering Clocks, Number System, Percentages, Profit/Loss, Time & Work, Averages, and Simple Interest.",
        45,  # 45 minutes duration
        json.dumps(questions),
        1,
        end_time
    ))
    
    conn.commit()
    conn.close()
    
    print(f"✅ Created aptitude test with 20 questions!")
    print(f"   Test will be available until: {end_time}")
    print(f"   Topics: Clocks, Number System, Percentages, Profit/Loss, Time & Work, Averages, SI")

if __name__ == "__main__":
    seed_aptitude_test()
