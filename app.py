from flask import Flask, render_template, request, redirect
import psycopg2
from dotenv import load_dotenv
import os

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    session
)

from flask_bcrypt import Bcrypt
from flask_session import Session
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer
)

from reportlab.lib.styles import getSampleStyleSheet

from reportlab.lib.pagesizes import letter

import pandas as pd

from flask import send_file

load_dotenv()

app = Flask(__name__)

app.secret_key = "goalsphere_secret"

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"

Session(app)

bcrypt = Bcrypt(app)


@app.route("/register", methods=["GET","POST"])





def register():

    if request.method == "POST":

        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        hashed_password = bcrypt.generate_password_hash(
            password
        ).decode("utf-8")

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO users
            (username, email, password)
            VALUES (%s,%s,%s)
        """, (
            username,
            email,
            hashed_password
        ))

        conn.commit()

        cur.close()
        conn.close()

        return redirect("/login")

    return render_template("register.html")

def get_db_connection():
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=os.getenv("DB_PORT")
    )
    return conn

@app.route("/login", methods=["GET","POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, username, password
            FROM users
            WHERE email=%s
        """, (email,))

        user = cur.fetchone()

        cur.close()
        conn.close()

        if user and bcrypt.check_password_hash(
            user[2],
            password
        ):

            session["user_id"] = user[0]
            session["username"] = user[1]

            return redirect("/")

    return render_template("login.html")

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")

@app.route("/")
def dashboard():

    if "user_id" not in session:
        return redirect("/login")

    conn = get_db_connection()
    cur = conn.cursor()

    # ================= GOALS =================

    cur.execute("""
        SELECT id, title, goal_type,
        priority, progress, deadline
        FROM goals
        WHERE user_id=%s
        ORDER BY id DESC
    """, (session["user_id"],))

    goals = cur.fetchall()

    # ================= ACTIVITIES =================

    cur.execute("""
        SELECT id, title, activity_date,
        activity_time, category
        FROM activities
        WHERE user_id=%s
        ORDER BY activity_date ASC
    """, (session["user_id"],))

    activities = cur.fetchall()

    # ================= TOTAL GOALS =================

    cur.execute("""
        SELECT COUNT(*)
        FROM goals
        WHERE user_id=%s
    """, (session["user_id"],))

    total_goals = cur.fetchone()[0]

    # ================= COMPLETED GOALS =================

    cur.execute("""
        SELECT COUNT(*)
        FROM goals
        WHERE progress >= 100
        AND user_id=%s
    """, (session["user_id"],))

    completed_goals = cur.fetchone()[0]

    # ================= AVG PROGRESS =================

    cur.execute("""
        SELECT COALESCE(AVG(progress),0)
        FROM goals
        WHERE user_id=%s
    """, (session["user_id"],))

    avg_progress = round(cur.fetchone()[0], 1)

    # ================= TOTAL ACTIVITIES =================

    cur.execute("""
        SELECT COUNT(*)
        FROM activities
        WHERE user_id=%s
    """, (session["user_id"],))

    total_activities = cur.fetchone()[0]

    productivity_score = round(
        (avg_progress + (completed_goals * 10)) / 2,
        1
    )

    # ================= CATEGORY ANALYTICS =================

    cur.execute("""
        SELECT category, COUNT(*)
        FROM activities
        WHERE user_id=%s
        GROUP BY category
    """, (session["user_id"],))

    category_data = cur.fetchall()

    categories = [row[0] for row in category_data]
    category_count = [row[1] for row in category_data]

    # ================= PROGRESS DATA =================

    cur.execute("""
        SELECT title, progress
        FROM goals
        WHERE user_id=%s
        ORDER BY id ASC
    """, (session["user_id"],))

    progress_data = cur.fetchall()

    goal_titles = [row[0] for row in progress_data]
    goal_progress = [row[1] for row in progress_data]

    # ================= HABITS =================

    cur.execute("""
        SELECT id, title,
        frequency, streak,
        completed
        FROM habits
        WHERE user_id=%s
        ORDER BY id DESC
    """, (session["user_id"],))

    habits = cur.fetchall()

    # ================= HABIT ANALYTICS =================

    cur.execute("""
        SELECT COUNT(*)
        FROM habits
        WHERE user_id=%s
    """, (session["user_id"],))

    total_habits = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*)
        FROM habits
        WHERE completed = TRUE
        AND user_id=%s
    """, (session["user_id"],))

    completed_habits = cur.fetchone()[0]

    habit_score = 0

    if total_habits > 0:

        habit_score = round(
            (completed_habits / total_habits) * 100,
            1
        )

    # ================= MATRIX TASKS =================

    cur.execute("""
        SELECT id, title, quadrant
        FROM matrix_tasks
        WHERE user_id=%s
        ORDER BY id DESC
    """, (session["user_id"],))

    matrix_tasks = cur.fetchall()

    # ================= ACHIEVEMENTS =================

    cur.execute("""
        SELECT id, title,
        description, xp,
        unlocked
        FROM achievements
    """)

    achievements = cur.fetchall()

    # ================= XP CALCULATION =================

    xp_total = 0

    xp_total += completed_goals * 100
    xp_total += completed_habits * 50

    level = int(xp_total / 500) + 1

    # ================= AI PRODUCTIVITY INSIGHT =================

    insights = []

    # PRODUCTIVITY STATUS

    if productivity_score >= 80:

        insights.append({
            "type": "success",
            "title": "Excellent Productivity",
            "message":
            "Your productivity performance is outstanding this period."
        })

    elif productivity_score >= 50:

        insights.append({
            "type": "warning",
            "title": "Stable Productivity",
            "message":
            "Your productivity is stable but can still improve."
        })

    else:

        insights.append({
            "type": "danger",
            "title": "Low Productivity",
            "message":
            "Your productivity score is currently low. Focus on priority tasks."
        })

    # HABIT CONSISTENCY

    if habit_score >= 70:

        insights.append({
            "type": "success",
            "title": "Strong Habit Consistency",
            "message":
            "Your habits are consistently maintained."
        })

    else:

        insights.append({
            "type": "warning",
            "title": "Habit Improvement Needed",
            "message":
            "Try maintaining your habits more consistently."
        })

    # BURNOUT DETECTION

    if total_activities >= 15:

        insights.append({
            "type": "danger",
            "title": "Potential Burnout Detected",
            "message":
            "Too many activities scheduled. Consider resting and prioritizing."
        })

    # GOAL COMPLETION

    if completed_goals >= 5:

        insights.append({
            "type": "success",
            "title": "Goal Completion Momentum",
            "message":
            "You are achieving goals consistently. Keep the momentum."
        })

    cur.close()
    conn.close()

    return render_template(
        "dashboard.html",
        goals=goals,
        activities=activities,
        total_goals=total_goals,
        completed_goals=completed_goals,
        avg_progress=avg_progress,
        total_activities=total_activities,
        productivity_score=productivity_score,
        categories=categories,
        category_count=category_count,
        goal_titles=goal_titles,
        goal_progress=goal_progress,
        habits=habits,
        total_habits=total_habits,
        completed_habits=completed_habits,
        habit_score=habit_score,
        matrix_tasks=matrix_tasks,
        achievements=achievements,
        xp_total=xp_total,
        level=level,
        insights=insights
    )

@app.route("/add-goal", methods=["POST"])
def add_goal():

    if "user_id" not in session:
        return redirect("/login")

    title = request.form["title"]
    goal_type = request.form["goal_type"]
    priority = request.form["priority"]
    progress = request.form["progress"]
    deadline = request.form["deadline"]

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO goals
        (
            title,
            goal_type,
            priority,
            progress,
            deadline,
            user_id
        )
        VALUES (%s,%s,%s,%s,%s,%s)
    """, (
        title,
        goal_type,
        priority,
        progress,
        deadline,
        session["user_id"]
    ))

    conn.commit()

    cur.close()
    conn.close()

    return redirect("/")


@app.route("/add-activity", methods=["POST"])
def add_activity():

    if "user_id" not in session:
        return redirect("/login")

    title = request.form["title"]
    activity_date = request.form["activity_date"]
    activity_time = request.form["activity_time"]
    category = request.form["category"]

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO activities
        (
            title,
            activity_date,
            activity_time,
            category,
            user_id
        )
        VALUES (%s,%s,%s,%s,%s)
    """, (
        title,
        activity_date,
        activity_time,
        category,
        session["user_id"]
    ))

    conn.commit()

    cur.close()
    conn.close()

    return redirect("/")

@app.route("/add-habit", methods=["POST"])
def add_habit():

    if "user_id" not in session:
        return redirect("/login")

    title = request.form["title"]
    frequency = request.form["frequency"]

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO habits
        (
            title,
            frequency,
            user_id
        )
        VALUES (%s,%s,%s)
    """, (
        title,
        frequency,
        session["user_id"]
    ))

    conn.commit()

    cur.close()
    conn.close()

    return redirect("/")


@app.route("/delete-goal/<int:id>")
def delete_goal(id):

    if "user_id" not in session:
        return redirect("/login")

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        DELETE FROM goals
        WHERE id=%s
    """, (id,))

    conn.commit()

    cur.close()
    conn.close()

    return redirect("/")


@app.route("/update-progress/<int:id>", methods=["POST"])
def update_progress(id):


    if "user_id" not in session:
        return redirect("/login")    
    progress = request.form["progress"]

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE goals
        SET progress=%s
        WHERE id=%s
    """, (progress, id))

    conn.commit()

    cur.close()
    conn.close()

    return redirect("/")


@app.route("/complete-habit/<int:id>")
def complete_habit(id):


    if "user_id" not in session:
        return redirect("/login")
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE habits
        SET completed = TRUE,
        streak = streak + 1
        WHERE id=%s
    """, (id,))

    conn.commit()

    cur.close()
    conn.close()

    return redirect("/")

@app.route("/add-matrix-task", methods=["POST"])
def add_matrix_task():

    if "user_id" not in session:
        return redirect("/login")

    title = request.form["title"]
    quadrant = request.form["quadrant"]

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO matrix_tasks
        (
            title,
            quadrant,
            user_id
        )
        VALUES (%s,%s,%s)
    """, (
        title,
        quadrant,
        session["user_id"]
    ))

    conn.commit()

    cur.close()
    conn.close()

    return redirect("/")

@app.route("/export-pdf")
def export_pdf():

    if "user_id" not in session:
        return redirect("/login")

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT title,
        goal_type,
        priority,
        progress,
        deadline
        FROM goals
        WHERE user_id=%s
    """, (session["user_id"],))

    goals = cur.fetchall()

    cur.close()
    conn.close()

    pdf_path = "exports/goals_report.pdf"

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=letter
    )

    styles = getSampleStyleSheet()

    elements = []

    title = Paragraph(
        "GoalSphere Productivity Report",
        styles["Title"]
    )

    elements.append(title)
    elements.append(Spacer(1,20))

    for goal in goals:

        text = f"""
        <b>Goal:</b> {goal[0]}<br/>
        <b>Type:</b> {goal[1]}<br/>
        <b>Priority:</b> {goal[2]}<br/>
        <b>Progress:</b> {goal[3]}%<br/>
        <b>Deadline:</b> {goal[4]}
        """

        elements.append(
            Paragraph(text, styles["BodyText"])
        )

        elements.append(Spacer(1,15))

    doc.build(elements)

    return send_file(
        pdf_path,
        as_attachment=True
    )

@app.route("/export-excel")
def export_excel():

    if "user_id" not in session:
        return redirect("/login")

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT title,
        goal_type,
        priority,
        progress,
        deadline
        FROM goals
        WHERE user_id=%s
    """, (session["user_id"],))

    goals = cur.fetchall()

    cur.close()
    conn.close()

    df = pd.DataFrame(
        goals,
        columns=[
            "Title",
            "Goal Type",
            "Priority",
            "Progress",
            "Deadline"
        ]
    )

    excel_path = "exports/goals_report.xlsx"

    df.to_excel(
        excel_path,
        index=False
    )

    return send_file(
        excel_path,
        as_attachment=True
    )

if __name__ == "__main__":
    app.run(debug=True)