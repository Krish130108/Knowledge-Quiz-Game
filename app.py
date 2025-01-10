from flask import Flask, render_template, redirect, request, session, g
from flask_session import Session
from cs50 import SQL
from werkzeug.security import check_password_hash, generate_password_hash
import json
from random import shuffle
from datetime import datetime

from helpers import apology, login_required
#flask --app app.py --debug run

# Configure application
app = Flask(__name__)

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///quiz.db")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.before_request
def before_request():
    g.is_admin = session.get("user_id") == 1  # Check if the user is an admin


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        password = request.form.get("password")

        if not request.form.get("username"):
            return apology("No username!", 403)

        # Ensure password was submitted
        if not request.form.get("password"):
            return apology("Must provide password", 403)
        
       # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], str(password)):
            return apology("Invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/")
def index():
    if not "user_id" in session:
        return render_template("index.html")
    
    else:
        user_id = session["user_id"]
        username = db.execute("SELECT username FROM users WHERE id=?", user_id)
        #print(username)
        username = username[0].get("username")

        return render_template("index.html", username=username)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name")
        dob = request.form.get("birthdate")
        password = request.form.get("password")

        if not name:
            return apology("Must provide name!", 403)
        
        if not dob:
            return apology("Must provide date of birth!", 403)
        
        if not password:
            return apology("Must provide password!", 403)
        
        if not request.form.get("confirmation"):
            return apology("Must provide confirmation password!", 403)
        
        if password != request.form.get("confirmation"):
            return apology("Password must match confirmation password!", 403)
        
        dob_date = datetime.strptime(dob, "%Y-%m-%d")
        today = datetime.today()
        age = today.year - dob_date.year - ((today.month, today.day) < (dob_date.month, dob_date.day))
    
        if age < 3:
            return apology("You must be at least 3 years old to register!", 403)
        
        username = name[0:3] + str(age)

        try:
            db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", username, generate_password_hash(password))
        except ValueError:
            apology("Username already exists!")
        
        return redirect("/login")
            
    else:
        return render_template("register.html")


def load_questions(topic, difficulty):
        with open("questions_answers.json", "r") as file:
            questions = json.load(file)

        return questions[topic][difficulty]


@app.route("/quiz", methods=["GET", "POST"])
@login_required
def quiz():
    if request.method == "POST":
        topic = request.form.get("topic")
        difficulty = request.form.get("difficulty")

        if not topic or not difficulty:
            return apology("Topic/difficulty not chosen!")

        # Load questions from a file
        questions = load_questions(topic.title(), difficulty.title())
        shuffle(questions)

        if not questions:
            return apology("Doesn't exist!")
        
        session["topic"] = topic
        session["questions"] = questions
        session["score"] = 0
        session["current_question_index"] = 0
        session["difficulty"] = difficulty

        return redirect("/play")

    return render_template("quiz.html")


@app.route("/play", methods=["GET", "POST"])
@login_required
def play():
    questions = session.get("questions", [])

    if session["current_question_index"] + 1 >= len(questions):
            return redirect("/results")

    # Handle form submission for answer or next
    if request.method == "POST":
        if "submit_answer" in request.form:
            selected_answer = request.form.get("answer")
            correct_answer = questions[session["current_question_index"]]["correct_answer"]
            
            session["selected_answer"] = selected_answer
            session["correct_answer"] = correct_answer
            session["show_feedback"] = True

            # Update score if the answer is correct
            if selected_answer == correct_answer:
                session["score"] += 1

        elif "next" in request.form:
            session["show_feedback"] = False
            session["current_question_index"] += 1

    current_question = questions[session["current_question_index"]]
    options = questions[session["current_question_index"]]["options"]
    shuffle(options)

    return render_template("play.html", question=current_question, options=options)


def get_grade(percentage):
    if percentage == 100:
        return {"A**": "Perfect Score! You are the GOAT 🐐"}
    
    elif percentage >= 90:
        return {"GA": "Slay Queen/King 👑, you cooked 🔥"}
    
    elif percentage >= 75:
        return {"B": "Certified Flex 💪: You've got the drip, but there's room to max your grind!"}
    
    elif percentage >= 60:
        return {"C": "This Ain't It, Dawg 😩: You tried, but the glow-up arc is overdue."}
    
    elif percentage >= 45:
        return {"D": "Low-Key Not Slaying 🤷: We need to level up your game."}
    
    elif percentage >= 30:
        return {"E": "NPC Vibes 💬: We see you... but you're just vibing in the background, aren't you?"}
    
    elif percentage == 0:
        return {"Failure": "You didn't even get cooked atp, you were barbecued and sautéed 🍚"}
    
    else:
        return {"Z": "Literal 404 Error 📉: Skill not found. Reboot your brain and queue up for another round."}


@app.route("/results")
@login_required
def results():
    score = session.get("score", 0)
    user_id = session.get("user_id")
    topic = session.get("topic", [])
    difficulty = session.get("difficulty", [])

    total_questions = len(session.get("questions", []))
    percentage = round((score/total_questions) * 100, 2) if total_questions > 0 else 0

    grade = get_grade(percentage)

    db.execute("INSERT INTO quiz_results (user_id, topic, score, grade, difficulty) VALUES (?, ?, ?, ?, ?)", user_id, topic, score, list(grade.keys())[0], difficulty)

    return render_template("results.html", score=score, total=total_questions, percentage=percentage, grade=grade)


@app.route("/admin_user_report", methods=["GET", "POST"])
@login_required
def admin_user_report():
    rows = db.execute("SELECT id, username FROM users ORDER BY id")

    if request.method == "POST":
        userId = request.form.get("user_id")
        
        if not userId:
            apology("Enter a username!")
        
        user = db.execute("SELECT * FROM users WHERE id = ?", userId)

        if not user:
            return apology("User ID does not exist!")
       
        results = db.execute("SELECT topic, difficulty, grade FROM quiz_results WHERE user_id = ?", userId)

        return render_template("user_report.html", results=results, selected_user=user[0])

    return render_template("admin_user_report.html", rows=rows)


@app.route("/admin_topic_report", methods=["GET", "POST"])
@login_required
def admin_topic_report():
    if request.method == "POST":
        # Get the selected topic and difficulty from the form
        topic = request.form.get("topic")
        difficulty = request.form.get("difficulty")

        if not topic or not difficulty:
            return apology("Please select a topic and difficulty level.")

        avg_score_result = db.execute("SELECT AVG(score) FROM quiz_results WHERE topic=? AND difficulty=?", topic.title(), difficulty.lower())
        highest_score_result = db.execute("SELECT MAX(score) FROM quiz_results WHERE topic=? AND difficulty=?", topic.title(), difficulty.lower())
        #print(avg_score_result)
        #print(highest_score_result)

        if not avg_score_result or not highest_score_result:
            return apology("No average score/high score available!")
        
        avg_score = avg_score_result[0]['AVG(score)'] if avg_score_result else None
        highest_score = highest_score_result[0]['MAX(score)'] if highest_score_result else None

        max_score_user_id = db.execute("SELECT user_id FROM quiz_results WHERE score=?", highest_score)

        if not max_score_user_id:
            return apology("High score doesn't exist")
        
        max_score_usernames = []

        for user in max_score_user_id:
            user_id = user['user_id']
            user_result = db.execute("SELECT username FROM users WHERE id=?", user_id)

            if user_result:
                max_score_usernames.append(user_result[0]['username'])

        print(max_score_usernames)
        
        return render_template("topic_report.html", avg_score=avg_score, highest_score=highest_score, max_score_user=max_score_usernames, topic=topic, difficulty=difficulty)

    return render_template("admin_topic_report.html")


@app.route("/report")
@login_required
def report():
    return apology("Option unavailable currently (still coding)")


@app.route("/history")
@login_required
def history():
    return apology("Option unavailable currently (still coding)")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")