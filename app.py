from flask import Flask, render_template, request, redirect, url_for, session
import random
from datetime import datetime

app = Flask(__name__)  # ← You were missing this
app.secret_key = 'supersecretkey'

# In-memory data storage
students = {}
questions = []
responses = []
next_student_id = 1
topics = ["Math", "Science", "History", "Language"]

# ... rest of your code remains the same ...


def init_questions():
    questions.clear()
    questions.extend([
        {
            'id': 1,
            'topic': 'Math',
            'difficulty': 0.4,
            'text': 'What is 5 + 7?',
            'options': ['10', '11', '12', '13'],
            'correct': '12',
            'explanation': '5 + 7 = 12'
        },
        {
            'id': 2,
            'topic': 'Science',
            'difficulty': 0.5,
            'text': 'Which planet is known as the Red Planet?',
            'options': ['Earth', 'Mars', 'Jupiter', 'Venus'],
            'correct': 'Mars',
            'explanation': 'Mars is called the Red Planet because of its reddish appearance.'
        },
        {
            'id': 3,
            'topic': 'History',
            'difficulty': 0.5,
            'text': 'Who was the first President of the United States?',
            'options': ['Abraham Lincoln', 'George Washington', 'Thomas Jefferson', 'John Adams'],
            'correct': 'George Washington',
            'explanation': 'George Washington served as the first U.S. president from 1789 to 1797.'
        },
        {
            'id': 4,
            'topic': 'Math',
            'difficulty': 0.6,
            'text': 'What is the square root of 64?',
            'options': ['6', '7', '8', '9'],
            'correct': '8',
            'explanation': 'The square root of 64 is 8.'
        },
        {
            'id': 5,
            'topic': 'Science',
            'difficulty': 0.7,
            'text': 'What gas do plants absorb from the atmosphere?',
            'options': ['Oxygen', 'Nitrogen', 'Carbon Dioxide', 'Hydrogen'],
            'correct': 'Carbon Dioxide',
            'explanation': 'Plants absorb carbon dioxide for photosynthesis.'
        }
    ])

# Helper functions
def update_student_performance(student_id, topic, is_correct):
    student = students[student_id]
    if topic not in student['performance']['topics']:
        student['performance']['topics'][topic] = {'correct': 0, 'total': 0}
    student['performance']['topics'][topic]['total'] += 1
    if is_correct:
        student['performance']['topics'][topic]['correct'] += 1

def get_next_topic(student_id):
    student = students[student_id]
    topics_data = student['performance']['topics']
    
    if not topics_data:
        return random.choice(topics)
    
    weakest_topic = None
    min_accuracy = 101  
    for topic, data in topics_data.items():
        accuracy = (data['correct'] / data['total']) * 100
        if accuracy < min_accuracy:
            min_accuracy = accuracy
            weakest_topic = topic
    
    return weakest_topic or random.choice(topics)

def get_question(topic, asked_questions):
    topic_questions = [q for q in questions if q['topic'] == topic and q['id'] not in asked_questions]
    if topic_questions:
        return random.choice(topic_questions)
    all_questions = [q for q in questions if q['id'] not in asked_questions]
    if all_questions:
        return random.choice(all_questions)
    return None

# Initialize questions at startup
init_questions()

# Routes
@app.route('/')
def home():
    return render_template('index.html', students=students.values())

@app.route('/register', methods=['POST'])
def register_student():
    global next_student_id
    name = request.form['name']
    student_id = next_student_id
    students[student_id] = {
        'id': student_id,
        'name': name,
        'performance': {'topics': {}},
        'last_updated': datetime.now().isoformat()
    }
    next_student_id += 1
    return redirect(url_for('home'))

@app.route('/student/<int:student_id>')
def student_dashboard(student_id):
    student = students.get(student_id)
    if not student:
        return redirect(url_for('home'))
    
    student_responses = [r.copy() for r in responses if r['student_id'] == student_id]
    for response in student_responses:
        question = next((q for q in questions if q['id'] == response['question_id']), None)
        if question:
            response['question_text'] = question['text']
            response['topic'] = question['topic']
    
    return render_template('dashboard.html', 
                           student=student, 
                           responses=student_responses,
                           performance=student['performance'])

@app.route('/quiz/<int:student_id>')
def start_quiz(student_id):
    if student_id not in students:
        return redirect(url_for('home'))
    
    session.clear()
    session['student_id'] = student_id
    session['question_count'] = 0
    session['correct_count'] = 0
    session['asked_questions'] = []
    session['quiz_results'] = []
    
    return redirect(url_for('show_question'))

@app.route('/question')
def show_question():
    if 'student_id' not in session:
        return redirect(url_for('home'))
    
    topic = get_next_topic(session['student_id'])
    question = get_question(topic, session.get('asked_questions', []))
    
    if not question:
        return render_template('no_questions.html')
    
    session['current_question'] = question
    session['question_count'] = session.get('question_count', 0) + 1
    session['asked_questions'] = session.get('asked_questions', []) + [question['id']]
    
    return render_template('question.html', 
                           question=question,
                           question_count=session['question_count'])

@app.route('/answer', methods=['POST'])
def process_answer():
    if 'student_id' not in session or 'current_question' not in session:
        return redirect(url_for('home'))
    
    student_id = session['student_id']
    question = session['current_question']
    user_answer = request.form['response']
    
    is_correct = user_answer == question['correct']
    update_student_performance(student_id, question['topic'], is_correct)
    
    if is_correct:
        session['correct_count'] = session.get('correct_count', 0) + 1
    
    responses.append({
        'student_id': student_id,
        'question_id': question['id'],
        'response': user_answer,
        'timestamp': datetime.now().isoformat(),
        'correct': is_correct
    })
    
    session['quiz_results'].append({
        'question': question,
        'response': user_answer,
        'is_correct': is_correct,
        'correct_answer': question['correct'],
        'explanation': question['explanation']
    })
    
    students[student_id]['last_updated'] = datetime.now().isoformat()
    
    if session['question_count'] >= 5:
        return redirect(url_for('quiz_results'))
    
    return redirect(url_for('show_question'))

@app.route('/results')
def quiz_results():
    if 'quiz_results' not in session:
        return redirect(url_for('home'))
    
    quiz_results = session['quiz_results']
    student_id = session['student_id']
    student = students[student_id]
    question_count = session['question_count']
    correct_count = session['correct_count']
    
    session.clear()
    
    return render_template('results.html',
                           quiz_results=quiz_results,
                           student_name=student['name'],
                           student_id=student_id,
                           question_count=question_count,
                           correct_count=correct_count)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
