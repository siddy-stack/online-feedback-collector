import csv
from flask import Flask, render_template, request, redirect, url_for, session,jsonify,Response
import sqlite3
import logging
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
app.secret_key = "supersecretkey"  # required for sessions
DATABASE = "database.db"

# -----------------------------
# Admin credentials (simple)
# -----------------------------
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"


# -----------------------------
# Database helper
# -----------------------------
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


# -----------------------------
# Home Page – Feedback Form
# -----------------------------
@app.route("/")
def index():
    success = request.args.get("success")
    return render_template("index.html", success=success)


# -----------------------------
# Submit Feedback
# -----------------------------
@app.route("/submit-feedback", methods=["POST"])
def submit_feedback():
    name = request.form.get("name")
    email = request.form.get("email")
    rating = request.form.get("rating")
    comments = request.form.get("comments")

    conn = get_db_connection()
    conn.execute(
        "INSERT INTO feedback (name, email, rating, comments) VALUES (?, ?, ?, ?)",
        (name, email, rating, comments),
    )
    conn.commit()
    conn.close()

    return redirect(url_for("index", success=1))


# -----------------------------
# Admin Login
# -----------------------------
@app.route("/admin-login", methods=["GET", "POST"])
def admin_login():
    error = None

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            return redirect(url_for("admin_dashboard"))
        else:
            error = "Invalid username or password"

    return render_template("admin_login.html", error=error)


# -----------------------------
# Admin Dashboard (Protected)
# -----------------------------
@app.route("/admin-dashboard")
def admin_dashboard():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    conn = get_db_connection()

    feedbacks = conn.execute(
        "SELECT * FROM feedback ORDER BY date_submitted DESC"
    ).fetchall()

    total_feedback = conn.execute(
        "SELECT COUNT(*) FROM feedback"
    ).fetchone()[0]

    avg_rating = conn.execute(
        "SELECT AVG(rating) FROM feedback"
    ).fetchone()[0]

    # Rating distribution for chart
    rating_counts = conn.execute(
        """
        SELECT rating, COUNT(*) as count
        FROM feedback
        GROUP BY rating
        ORDER BY rating
        """
    ).fetchall()

    conn.close()

    # Prepare data for Chart.js
    ratings = [row["rating"] for row in rating_counts]
    counts = [row["count"] for row in rating_counts]

    return render_template(
        "admin.html",
        feedbacks=feedbacks,
        total_feedback=total_feedback,
        avg_rating=round(avg_rating, 2) if avg_rating else 0,
        ratings=ratings,
        counts=counts
    )

#-----------------------------------
#Delete Operation
#-----------------------------------

@app.route("/delete-feedback/<int:id>")
def delete_feedback(id):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    conn = get_db_connection()
    conn.execute("DELETE FROM feedback WHERE id = ?", (id,))
    conn.commit()
    conn.close()

    return redirect(url_for("admin_dashboard"))


# -----------------------------
# Logout
# -----------------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("admin_login"))

@app.route("/api/feedback", methods=["POST"])
def api_submit_feedback():
    data = request.get_json()

    # Basic validation
    if not data:
        return jsonify({"error": "No JSON data provided"}), 400

    name = data.get("name")
    email = data.get("email")
    rating = data.get("rating")
    comments = data.get("comments", "")

    if not all([name, email, rating]):
        return jsonify({"error": "Missing required fields"}), 400

    conn = get_db_connection()
    conn.execute(
        """
        INSERT INTO feedback (name, email, rating, comments)
        VALUES (?, ?, ?, ?)
        """,
        (name, email, rating, comments),
    )
    conn.commit()
    conn.close()

    return jsonify({
        "message": "Feedback logged successfully"
    }), 201

#-------------------------------------------
#---------Edit Feedback---------------------
#-------------------------------------------

@app.route("/edit-feedback/<int:id>", methods=["GET", "POST"])
def edit_feedback(id):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    conn = get_db_connection()

    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        rating = request.form.get("rating")
        comments = request.form.get("comments")

        conn.execute(
            """
            UPDATE feedback
            SET name = ?, email = ?, rating = ?, comments = ?
            WHERE id = ?
            """,
            (name, email, rating, comments, id),
        )
        conn.commit()
        conn.close()

        return redirect(url_for("admin_dashboard"))

    # GET request → load existing data
    feedback = conn.execute(
        "SELECT * FROM feedback WHERE id = ?", (id,)
    ).fetchone()
    conn.close()

    return render_template("edit_feedback.html", feedback=feedback)


@app.route("/api/feedback", methods=["GET"])
def api_get_feedback():
    conn = get_db_connection()
    feedbacks = conn.execute(
        "SELECT * FROM feedback ORDER BY date_submitted DESC"
    ).fetchall()
    conn.close()

    return jsonify([
        dict(feedback) for feedback in feedbacks
    ])

@app.route("/export-csv")
def export_csv():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    conn = get_db_connection()
    feedbacks = conn.execute(
        "SELECT * FROM feedback ORDER BY date_submitted DESC"
    ).fetchall()
    conn.close()

    def generate():
        yield "ID,Name,Email,Rating,Comments,Date Submitted\n"
        for f in feedbacks:
            yield f'{f["id"]},{f["name"]},{f["email"]},{f["rating"]},"{f["comments"]}",{f["date_submitted"]}\n'

    return Response(
        generate(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=feedback_data.csv"
        }
    )


# -----------------------------
# Run App
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)
