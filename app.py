from flask import Flask,render_template,redirect, url_for
from pymongo import DESCENDING
from flask import request
from pymongo import MongoClient
from bson.objectid import ObjectId  # Add this at the top
from datetime import datetime
from flask import session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import hashlib
from bson import ObjectId
import os
from werkzeug.utils import secure_filename
import qrcode
import io
from flask import send_file


app = Flask(__name__)
app.jinja_env.globals.update(now=datetime.now)
app.secret_key = 'your_secret_key_here'  # 🛡️ Needed for sessions

# Profile pic upload config
PROFILE_PIC_FOLDER = os.path.join('static', 'profile_pics')
os.makedirs(PROFILE_PIC_FOLDER, exist_ok=True)
app.config['PROFILE_PIC_FOLDER'] = PROFILE_PIC_FOLDER

# Question image upload config
QUESTION_IMAGE_FOLDER = os.path.join('static', 'question_images')
os.makedirs(QUESTION_IMAGE_FOLDER, exist_ok=True)
app.config['QUESTION_IMAGE_FOLDER'] = QUESTION_IMAGE_FOLDER




client = MongoClient("mongodb://localhost:27017/")  # replace with your Atlas URL if needed
contact_db = client["contact_db"]
messages_col = contact_db["messages"]


quiz_db = client["quiz_platform"]
quizzes_col = quiz_db["quizzes"]
responses_col = quiz_db["responses"] 
users_col = quiz_db["users"]
quiz_results_col = quiz_db["quiz_results"]
 # for quiz responses




@app.route('/')
def splash():
    return render_template('splash.html')


@app.route('/index')
def hello():
    recent_quizzes = quizzes_col.find().sort('_id', -1).limit(5)  # latest 5
    return render_template('index.html', recent_quizzes=recent_quizzes)


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        message = request.form.get('message')
            #  Store in MongoDB
        messages_col.insert_one({
            "name": name,
            "email": email,
            "message": message
        })

        # For now, just print to console (you can save later to DB or send email)
        print(f"Received message from {name} ({email}): {message}")
        return f"Thanks for contacting us, {name}!"
    return render_template('contact.html')

@app.route('/services')
def services():
    return render_template('services.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = 'user'
        profile_pic = request.files.get('profile_pic')
        # Check if user exists
        if users_col.find_one({"username": username}):
            flash("Username already exists.")
            return redirect(url_for('signup'))

        hashed_pw = generate_password_hash(password)
        pic_filename = None
        if profile_pic and profile_pic.filename:
            filename = secure_filename(profile_pic.filename)
            pic_path = os.path.join(app.config['PROFILE_PIC_FOLDER'], filename)
            profile_pic.save(pic_path)
            pic_filename = filename

        users_col.insert_one({
            "username": username,
            "password": hashed_pw,
            "role": role,
            "profile_pic": pic_filename  # ⬅️ Save filename to DB

        })

        flash("Signup successful. Please login.")
        return redirect(url_for('login'))

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = users_col.find_one({"username": username})
        if user and check_password_hash(user['password'], password):
            #  Login success
            session['username'] = user['username']
            session['role'] = user.get('role', 'user')  # default to 'user' if role is missing
            flash("Login successful!")

            return redirect(url_for('hello'))  # or 'dashboard' or 'profile'
        else:
            flash("Invalid username or password.")
            return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('username', None)
    flash("You have been logged out.")
    return redirect(url_for('login'))

@app.route('/create-quiz', methods=['GET', 'POST'])
def create_quiz():
    if 'username' not in session or session.get('role') != 'admin':
        flash("Only admins can create quizzes.")
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        category = request.form.get('category')
        duration = int(request.form.get('duration'))  # Add this line
        total = int(request.form.get('total_questions'))


        questions = []
        for i in range(total):
            q = request.form.get(f'question_{i}')
            opts = [
                request.form.get(f'option_{i}_1'),
                request.form.get(f'option_{i}_2'),
                request.form.get(f'option_{i}_3'),
                request.form.get(f'option_{i}_4')
            ]
            ans = request.form.get(f'answer_{i}')

            image_file = request.files.get(f'image_{i}')
            image_filename = None
            if image_file and image_file.filename != '':
               filename = secure_filename(image_file.filename)
               image_path = os.path.join(app.config['QUESTION_IMAGE_FOLDER'], filename)
               image_file.save(image_path)
               image_filename = f"question_images/{filename}"  #  store relative path from /static


            questions.append({
                "question": q,
                "options": opts,
                "answer": ans,
                "image": image_filename  # 🎯 Store image filename

            })

        quiz = {
            "title": title,
            "description": description,
            "category": category,
            "duration": duration,  # 👈 Add to stored quiz
            "questions": questions,
            "created_by": session.get('username')
        }

        result = quizzes_col.insert_one(quiz)
        flash("Quiz created successfully!", "success")
        return redirect(url_for('view_quiz', quiz_id=str(result.inserted_id)))

    return render_template('create_quiz.html')


@app.route('/quiz/<quiz_id>')
def view_quiz(quiz_id):
    quiz = quizzes_col.find_one({"_id": ObjectId(quiz_id)})
    return render_template('view_quiz.html', quiz=quiz)

@app.route('/quiz/<quiz_id>/qr')
def quiz_qr(quiz_id):
    quiz_url = request.url_root + 'take-quiz/' + quiz_id
    qr = qrcode.make(quiz_url)

    img_io = io.BytesIO()
    qr.save(img_io, 'PNG')
    img_io.seek(0)

    return send_file(img_io, mimetype='image/png')

@app.route('/take-quiz/<quiz_id>', methods=['GET', 'POST'])
def take_quiz(quiz_id):
    quiz = quizzes_col.find_one({"_id": ObjectId(quiz_id)})

    if not quiz:
        return "Quiz not found", 404

    # Ensure 'duration' exists and is valid
    if not quiz.get('duration'):
        quiz['duration'] = 1  # Default to 5 minutes

    if request.method == 'POST':
        user_answers = []
        score = 0
        streak = 0
        max_streak = 0

        for i, q in enumerate(quiz.get('questions', [])):
            user_answer = request.form.get(f'question_{i}')
            user_answers.append(user_answer)

            if user_answer == q.get('answer'):
                score += 1
                streak += 1
                max_streak = max(max_streak, streak)
            else:
                streak = 0
                
        # ⏱Get remaining time if you’re tracking it from frontend
        time_left = request.form.get('time_left', 0)
        try:
            time_left = int(time_left)
        except:
            time_left = 0

        # GAMIFICATION BONUS SYSTEM
        bonus = 0
        if quiz.get('category') == 'Entertainment':
            if max_streak >= 3:
                bonus += 5  # Streak bonus
            if time_left > 0:
                bonus += int(time_left * 0.5)  # Timer bonus

        total_score = score * 10 + bonus  # base score is 10 pts per correct

        #  Store the result
        quiz_results_col.insert_one({
            "quiz_id": ObjectId(quiz_id),
            "user": session.get('username', 'guest'),
            "score": total_score,
            "raw_score": score,
            "bonus": bonus,
            "timestamp": datetime.utcnow()
        })

        return render_template("quiz_result.html", score=total_score, raw_score=score, bonus=bonus, total=len(quiz['questions']))

    return render_template('take_quiz.html', quiz=quiz)


@app.route('/quizzes')
def all_quizzes():
    category = request.args.get('category')
    if category:
        quizzes = quizzes_col.find({'category': category})
    else:
        quizzes = quizzes_col.find()

    return render_template('quiz_list.html', quizzes=quizzes, selected_category=category)

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'username' not in session:
        flash("You need to log in to view your profile.")
        return redirect(url_for('login'))

    username = session['username']
    user = users_col.find_one({"username": username})
    user_quizzes = quizzes_col.find({"created_by": username})

    if request.method == 'POST':
        new_username = request.form['username']
        new_password = request.form['password']
        profile_pic = request.files.get('profile_pic')

        update_data = {
            "username": new_username,
            "password": generate_password_hash(new_password)
        }

        if profile_pic and profile_pic.filename:
            filename = secure_filename(profile_pic.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            profile_pic.save(file_path)
            update_data["profile_pic"] = filename

        # Update DB
        users_col.update_one({"username": username}, {"$set": update_data})

        # Update session username if changed
        session['username'] = new_username

        flash("Profile updated successfully!")
        return redirect(url_for('profile'))

    profile_pic = user.get('profile_pic', 'default.jpg')
    is_admin = user.get('role') == 'admin'

    return render_template(
        'profile.html',
        username=username,
        profile_pic=profile_pic,
        quizzes=user_quizzes,
        admin=is_admin,
        user=user  # 👈 pass full user object for form values
    )


@app.route('/quiz-analytics/<quiz_id>')
def quiz_analytics(quiz_id):
    quiz = quizzes_col.find_one({"_id": ObjectId(quiz_id)})
    if not quiz:
        return "Quiz not found", 404

    results = quiz_results_col.find({"quiz_id": ObjectId(quiz_id)})

    total_attempts = results.count()
    scores = [r['score'] for r in results]
    average_score = round(sum(scores) / total_attempts, 2) if total_attempts > 0 else 0

    # Optional: list latest 5 attempts
    recent_results = quiz_results_col.find(
        {"quiz_id": ObjectId(quiz_id)}
    ).sort("timestamp", DESCENDING).limit(5)

    return render_template("quiz_analytics.html", quiz=quiz, total_attempts=total_attempts,
                           average_score=average_score, recent_results=recent_results)
@app.route('/admin/quizzes')
def admin_quizzes():
    if 'username' not in session or session.get('role') != 'admin':
        flash("Admins only.")
        return redirect(url_for('login'))

    all_quizzes = quizzes_col.find()
    return render_template('admin_quizzes.html', quizzes=all_quizzes)

@app.route('/quiz/<quiz_id>/edit', methods=['GET', 'POST'])
def edit_quiz(quiz_id):
    if 'username' not in session or session.get('role') != 'admin':
        flash("Admins only.")
        return redirect(url_for('login'))

    quiz = quizzes_col.find_one({"_id": ObjectId(quiz_id)})

    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        category = request.form.get('category')
        total = int(request.form.get('total_questions'))

        questions = []
        for i in range(total):
            q = request.form.get(f'question_{i}')
            opts = [
                request.form.get(f'option_{i}_1'),
                request.form.get(f'option_{i}_2'),
                request.form.get(f'option_{i}_3'),
                request.form.get(f'option_{i}_4')
            ]
            ans = request.form.get(f'answer_{i}')
            questions.append({
                "question": q,
                "options": opts,
                "answer": ans
            })

        quizzes_col.update_one(
            {"_id": ObjectId(quiz_id)},
            {"$set": {
                "title": title,
                "description": description,
                "category": category,
                "questions": questions
            }}
        )
        flash("Quiz updated!")
        return redirect(url_for('admin_quizzes'))

    return render_template('edit_quiz.html', quiz=quiz)

@app.route('/quiz/<quiz_id>/delete')
def delete_quiz(quiz_id):
    if 'username' not in session or session.get('role') != 'admin':
        flash("Admins only.")
        return redirect(url_for('login'))

    quizzes_col.delete_one({"_id": ObjectId(quiz_id)})
    flash("Quiz deleted.")
    return redirect(url_for('admin_quizzes'))


@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'username' not in session:
        return redirect('/login')

    username = session['username']
    user = users_col.find_one({'username': username})

    # Update profile if form submitted
    if request.method == 'POST':
        new_username = request.form.get('username')
        new_password = request.form.get('password')

        users_col.update_one(
            {'_id': user['_id']},
            {'$set': {
                'username': new_username,
                'password': generate_password_hash(new_password)

            }}
        )
        session['username'] = new_username
        flash('Profile updated successfully!', 'info')
        return redirect('/dashboard')

    # Get user's quiz results
    recent_results = quiz_results_col.find({'user': username}).sort('timestamp', -1).limit(5)
    full_history = quiz_results_col.find({'user': username}).sort('timestamp', -1)

    return render_template('dashboard.html', user=user, recent_results=recent_results, history=full_history)

@app.route('/my-results')
def my_results():
    username = session.get('username')
    if not username:
        return redirect('/login')

    cursor = quiz_results_col.find({"user": username}).sort("timestamp", -1)
    results = list(cursor)  # convert cursor to list
    return render_template("my_results.html", results=results)

@app.route('/leaderboard')
def global_leaderboard():
    # Aggregate total scores per user
    pipeline = [
        {"$group": {
            "_id": "$user",
            "total_score": {"$sum": "$score"},
            "attempts": {"$sum": 1},
            "last_played": {"$max": "$timestamp"}
        }},
        {"$sort": {"total_score": -1}},
        {"$limit": 10}
    ]

    top_players_raw = list(quiz_results_col.aggregate(pipeline))

    top_players = []
    for player in top_players_raw:
        user = users_col.find_one({"username": player["_id"]}) or {}
        player["profile_pic"] = user.get("profile_pic", None)
        top_players.append(player)

    return render_template("global_leaderboard.html", top_players=top_players)

if __name__ == '__main__':
    app.run(debug=True)
