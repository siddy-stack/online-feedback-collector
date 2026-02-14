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

    # -------- Query Params --------
    page = request.args.get("page", 1, type=int)
    search = request.args.get("search", "")
    rating_filter = request.args.get("rating", "")
    sort = request.args.get("sort", "date_desc")

    per_page = 5
    offset = (page - 1) * per_page

    # -------- WHERE conditions --------
    where_clauses = []
    params = []

    # Search (name, email, comments)
    if search:
        where_clauses.append(
            "(name LIKE ? OR email LIKE ? OR comments LIKE ?)"
        )
        keyword = f"%{search}%"
        params.extend([keyword, keyword, keyword])

    # Rating filter
    if rating_filter:
        where_clauses.append("rating = ?")
        params.append(rating_filter)

    where_sql = ""
    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    # -------- Sorting --------
    order_by = {
        "date_desc": "date_submitted DESC",
        "date_asc": "date_submitted ASC",
        "rating_desc": "rating DESC",
        "rating_asc": "rating ASC",
    }.get(sort, "date_submitted DESC")

    # -------- Count for pagination --------
    total_feedback = conn.execute(
        f"SELECT COUNT(*) FROM feedback {where_sql}",
        params
    ).fetchone()[0]

    total_pages = (total_feedback + per_page - 1) // per_page

    # -------- Fetch data --------
    feedbacks = conn.execute(
        f"""
        SELECT * FROM feedback
        {where_sql}
        ORDER BY {order_by}
        LIMIT ? OFFSET ?
        """,
        params + [per_page, offset]
    ).fetchall()

    # -------- Stats (for dashboard) --------
    avg_rating = conn.execute(
        "SELECT AVG(rating) FROM feedback"
    ).fetchone()[0]

    rating_counts = conn.execute(
        """
        SELECT rating, COUNT(*) AS count
        FROM feedback
        GROUP BY rating
        ORDER BY rating
        """
    ).fetchall()

    conn.close()

    ratings = [row["rating"] for row in rating_counts]
    counts = [row["count"] for row in rating_counts]

    return render_template(
        "admin.html",
        feedbacks=feedbacks,
        total_feedback=total_feedback,
        avg_rating=round(avg_rating, 2) if avg_rating else 0,
        ratings=ratings,
        counts=counts,
        page=page,
        total_pages=total_pages,
        search=search,
        rating_filter=rating_filter,
        sort=sort
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
