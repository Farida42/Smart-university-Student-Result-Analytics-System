from flask import Flask, render_template, request, redirect, session, jsonify, Response, send_file
from werkzeug.security import check_password_hash, generate_password_hash
from db import get_connection

import csv
from io import StringIO, BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

app = Flask(__name__)
app.secret_key = "super-secret-key-change-this"

# ---------------- Helpers ----------------
def calc_grade(total_percent: float):
    if total_percent >= 80: return ("A+", 4.00)
    if total_percent >= 75: return ("A", 3.75)
    if total_percent >= 70: return ("A-", 3.50)
    if total_percent >= 65: return ("B+", 3.25)
    if total_percent >= 60: return ("B", 3.00)
    if total_percent >= 55: return ("B-", 2.75)
    if total_percent >= 50: return ("C+", 2.50)
    if total_percent >= 45: return ("C", 2.25)
    if total_percent >= 40: return ("D", 2.00)
    return ("F", 0.00)

def require_role(role):
    return session.get("role") == role

# ---------------- Auth ----------------
@app.route("/")
def home():
    return redirect("/login")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip()
        password = request.form["password"].strip()

        con = get_connection()
        cur = con.cursor(dictionary=True)
        cur.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cur.fetchone()
        cur.close(); con.close()

        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["user_id"]
            session["role"] = user["role"]

            if user["role"] == "admin":
                return redirect("/admin/dashboard")
            if user["role"] == "teacher":
                return redirect("/teacher/marks")
            return redirect("/student/dashboard")

        return render_template("login.html", error="Invalid email or password")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# ---------------- STUDENT ----------------
@app.route("/student/dashboard")
def student_dashboard():
    if not require_role("student"):
        return redirect("/login")
    return render_template("student_dashboard.html", title="Student Dashboard")

@app.route("/student/gpa-trend")
def student_gpa_trend():
    if not require_role("student"):
        return jsonify({"error": "Unauthorized"}), 401

    user_id = session["user_id"]
    con = get_connection()
    cur = con.cursor(dictionary=True)

    cur.execute("SELECT student_id FROM students WHERE user_id=%s", (user_id,))
    s = cur.fetchone()
    if not s:
        cur.close(); con.close()
        return jsonify({"labels": [], "gpa": []})

    student_id = s["student_id"]

    cur.execute("""
        SELECT sem.name AS semester, AVG(r.grade_point) AS gpa
        FROM results r
        JOIN enrollments e ON r.enroll_id = e.enroll_id
        JOIN semesters sem ON e.semester_id = sem.semester_id
        WHERE e.student_id = %s AND r.is_published = 1
        GROUP BY sem.semester_id
        ORDER BY sem.year, sem.semester_id
    """, (student_id,))
    rows = cur.fetchall()
    cur.close(); con.close()

    labels = [row["semester"] for row in rows]
    gpa = [float(row["gpa"]) if row["gpa"] else 0 for row in rows]
    return jsonify({"labels": labels, "gpa": gpa})

@app.route("/student/cgpa")
def student_cgpa():
    if not require_role("student"):
        return jsonify({"error":"Unauthorized"}), 401

    user_id = session["user_id"]
    con = get_connection()
    cur = con.cursor(dictionary=True)

    cur.execute("SELECT student_id FROM students WHERE user_id=%s", (user_id,))
    s = cur.fetchone()
    if not s:
        cur.close(); con.close()
        return jsonify({"cgpa": 0, "total_credits": 0, "semesters": []})

    student_id = s["student_id"]

    cur.execute("""
      SELECT sem.semester_id, sem.name AS semester, sem.year,
             SUM(r.grade_point * c.credit) / NULLIF(SUM(c.credit), 0) AS gpa,
             SUM(c.credit) AS credits
      FROM results r
      JOIN enrollments e ON r.enroll_id = e.enroll_id
      JOIN courses c ON e.course_id = c.course_id
      JOIN semesters sem ON e.semester_id = sem.semester_id
      WHERE e.student_id = %s AND r.is_published = 1
      GROUP BY sem.semester_id
      ORDER BY sem.year, sem.semester_id
    """, (student_id,))
    sem_rows = cur.fetchall()

    cur.execute("""
      SELECT SUM(r.grade_point * c.credit) / NULLIF(SUM(c.credit), 0) AS cgpa,
             SUM(c.credit) AS total_credits
      FROM results r
      JOIN enrollments e ON r.enroll_id = e.enroll_id
      JOIN courses c ON e.course_id = c.course_id
      WHERE e.student_id = %s AND r.is_published = 1
    """, (student_id,))
    overall = cur.fetchone()

    cur.close(); con.close()

    semesters = []
    for row in sem_rows:
        semesters.append({
            "semester": row["semester"],
            "gpa": round(float(row["gpa"] or 0), 2),
            "credits": float(row["credits"] or 0)
        })

    cgpa = round(float(overall["cgpa"] or 0), 2)
    total_credits = float(overall["total_credits"] or 0)

    return jsonify({"cgpa": cgpa, "total_credits": total_credits, "semesters": semesters})

@app.route("/student/risk-status")
def student_risk_status():
    if not require_role("student"):
        return jsonify({"error":"Unauthorized"}), 401

    user_id = session["user_id"]
    con = get_connection()
    cur = con.cursor(dictionary=True)

    cur.execute("SELECT student_id FROM students WHERE user_id=%s", (user_id,))
    s = cur.fetchone()
    if not s:
        cur.close(); con.close()
        return jsonify({"risk":"unknown"})

    student_id = s["student_id"]

    cur.execute("""
      SELECT AVG(CASE WHEN a.total_class>0 THEN (a.attended_class/a.total_class)*100 ELSE 0 END) AS avg_att
      FROM attendance a
      JOIN enrollments e ON a.enroll_id = e.enroll_id
      WHERE e.student_id = %s
    """, (student_id,))
    att = cur.fetchone()
    avg_att = float(att["avg_att"] or 0)

    cur.execute("""
      SELECT AVG(r.grade_point) AS avg_gp,
             SUM(CASE WHEN r.letter_grade='F' THEN 1 ELSE 0 END) AS f_count
      FROM results r
      JOIN enrollments e ON r.enroll_id = e.enroll_id
      WHERE e.student_id = %s AND r.is_published = 1
    """, (student_id,))
    perf = cur.fetchone()
    avg_gp = float(perf["avg_gp"] or 0)
    f_count = int(perf["f_count"] or 0)

    cur.close(); con.close()

    risk = "low"
    if avg_att < 75 or avg_gp < 2.5 or f_count >= 2:
        risk = "high"
    elif avg_att < 85 or avg_gp < 3.0 or f_count == 1:
        risk = "medium"

    return jsonify({
        "risk": risk,
        "avg_attendance": round(avg_att, 2),
        "avg_gp": round(avg_gp, 2),
        "f_count": f_count
    })

@app.route("/student/marksheet.pdf")
def student_marksheet_pdf():
    if not require_role("student"):
        return redirect("/login")

    user_id = session["user_id"]
    con = get_connection()
    cur = con.cursor(dictionary=True)

    cur.execute("""
      SELECT u.name, u.email, s.student_id, s.dept, s.batch, s.section
      FROM users u JOIN students s ON u.user_id=s.user_id
      WHERE u.user_id=%s
    """, (user_id,))
    info = cur.fetchone()
    if not info:
        cur.close(); con.close()
        return "Student not found", 404

    cur.execute("""
      SELECT sem.name AS semester, c.code, c.title, c.credit,
             r.total_percent, r.letter_grade, r.grade_point
      FROM results r
      JOIN enrollments e ON r.enroll_id = e.enroll_id
      JOIN courses c ON e.course_id = c.course_id
      JOIN semesters sem ON e.semester_id = sem.semester_id
      WHERE e.student_id = %s AND r.is_published = 1
      ORDER BY sem.year, sem.semester_id, c.code
    """, (info["student_id"],))
    rows = cur.fetchall()
    cur.close(); con.close()

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    y = height - 50
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, y, "Smart University - Marksheet")
    y -= 25

    p.setFont("Helvetica", 10)
    p.drawString(50, y, f"Name: {info['name']} | Email: {info['email']}")
    y -= 15
    p.drawString(50, y, f"Dept: {info['dept']} | Batch: {info['batch']} | Section: {info['section']}")
    y -= 25

    p.setFont("Helvetica-Bold", 10)
    p.drawString(50, y, "Semester")
    p.drawString(150, y, "Course")
    p.drawString(330, y, "Credit")
    p.drawString(380, y, "Percent")
    p.drawString(450, y, "Grade")
    p.drawString(500, y, "GP")
    y -= 12
    p.line(50, y, width - 50, y)
    y -= 12

    p.setFont("Helvetica", 10)
    for r in rows:
        if y < 60:
            p.showPage()
            y = height - 50
            p.setFont("Helvetica", 10)

        p.drawString(50, y, str(r["semester"]))
        p.drawString(150, y, f"{r['code']} - {str(r['title'])[:25]}")
        p.drawRightString(360, y, f"{float(r['credit']):.1f}")
        p.drawRightString(430, y, f"{float(r['total_percent']):.2f}")
        p.drawString(450, y, str(r["letter_grade"]))
        p.drawRightString(540, y, f"{float(r['grade_point']):.2f}")
        y -= 14

    p.showPage()
    p.save()
    buffer.seek(0)

    return send_file(buffer, as_attachment=True, download_name="marksheet.pdf", mimetype="application/pdf")

# ---------------- TEACHER ----------------
@app.route("/teacher/marks")
def teacher_marks_page():
    if not require_role("teacher"):
        return redirect("/login")
    return render_template("teacher_marks.html", title="Marks Entry")

@app.route("/teacher/attendance")
def teacher_attendance_page():
    if not require_role("teacher"):
        return redirect("/login")
    return render_template("teacher_attendance.html", title="Attendance Entry")

@app.route("/teacher/enrollments")
def teacher_enrollments():
    if not require_role("teacher"):
        return jsonify({"error":"Unauthorized"}), 401

    user_id = session["user_id"]
    con = get_connection()
    cur = con.cursor(dictionary=True)

    cur.execute("SELECT teacher_id FROM teachers WHERE user_id=%s", (user_id,))
    t = cur.fetchone()
    if not t:
        cur.close(); con.close()
        return jsonify([])

    teacher_id = t["teacher_id"]

    cur.execute("""
      SELECT e.enroll_id, e.course_id, c.code, c.title,
             sem.name AS semester, sem.year,
             u.name AS student_name, u.email AS student_email
      FROM course_teachers ct
      JOIN courses c ON ct.course_id = c.course_id
      JOIN semesters sem ON ct.semester_id = sem.semester_id
      JOIN enrollments e ON e.course_id=ct.course_id AND e.semester_id=ct.semester_id
      JOIN students s ON e.student_id = s.student_id
      JOIN users u ON s.user_id = u.user_id
      WHERE ct.teacher_id = %s
        AND (ct.section IS NULL OR s.section = ct.section)
      ORDER BY sem.year, sem.semester_id, c.code, u.name
    """, (teacher_id,))
    rows = cur.fetchall()

    cur.close(); con.close()
    return jsonify(rows)

@app.route("/teacher/components/<int:course_id>")
def teacher_components(course_id):
    if not require_role("teacher"):
        return jsonify({"error":"Unauthorized"}), 401

    con = get_connection()
    cur = con.cursor(dictionary=True)
    cur.execute("""
      SELECT comp_id, name, max_marks, weight
      FROM mark_components
      WHERE course_id=%s
      ORDER BY comp_id
    """, (course_id,))
    rows = cur.fetchall()
    cur.close(); con.close()
    return jsonify(rows)

@app.route("/teacher/submit-marks", methods=["POST"])
def teacher_submit_marks():
    if not require_role("teacher"):
        return jsonify({"error":"Unauthorized"}), 401

    payload = request.get_json(force=True)
    enroll_id = int(payload["enroll_id"])
    course_id = int(payload["course_id"])
    items = payload.get("items", [])

    con = get_connection()
    cur = con.cursor(dictionary=True)

    cur.execute("""
      SELECT comp_id, max_marks, weight
      FROM mark_components
      WHERE course_id=%s
    """, (course_id,))
    comps = cur.fetchall()
    comp_map = {c["comp_id"]: c for c in comps}

    # upsert marks
    for it in items:
        comp_id = int(it["comp_id"])
        obtained = float(it["obtained_marks"])
        if comp_id not in comp_map:
            continue

        mx = float(comp_map[comp_id]["max_marks"])
        obtained = max(0.0, min(obtained, mx))

        cur.execute("""
          INSERT INTO marks(enroll_id, comp_id, obtained_marks)
          VALUES (%s,%s,%s)
          ON DUPLICATE KEY UPDATE obtained_marks=VALUES(obtained_marks)
        """, (enroll_id, comp_id, obtained))

    # calculate total percent
    total_percent = 0.0
    for comp_id, c in comp_map.items():
        mx = float(c["max_marks"])
        w = float(c["weight"])
        cur.execute("SELECT obtained_marks FROM marks WHERE enroll_id=%s AND comp_id=%s", (enroll_id, comp_id))
        m = cur.fetchone()
        obtained = float(m["obtained_marks"]) if m else 0.0
        total_percent += (obtained / mx) * w if mx > 0 else 0.0

    letter, gp = calc_grade(total_percent)

    # draft by default
    cur.execute("""
      INSERT INTO results(enroll_id, total_percent, letter_grade, grade_point, is_published)
      VALUES (%s,%s,%s,%s,0)
      ON DUPLICATE KEY UPDATE
        total_percent=VALUES(total_percent),
        letter_grade=VALUES(letter_grade),
        grade_point=VALUES(grade_point)
    """, (enroll_id, total_percent, letter, gp))

    con.commit()
    cur.close(); con.close()

    return jsonify({
        "message":"Marks saved (Draft). Admin will publish.",
        "total_percent": round(total_percent, 2),
        "letter_grade": letter,
        "grade_point": gp
    })

@app.route("/teacher/submit-attendance", methods=["POST"])
def teacher_submit_attendance():
    if not require_role("teacher"):
        return jsonify({"error":"Unauthorized"}), 401

    payload = request.get_json(force=True)
    enroll_id = int(payload["enroll_id"])
    total_class = max(0, int(payload.get("total_class", 0)))
    attended_class = max(0, int(payload.get("attended_class", 0)))
    if attended_class > total_class:
        attended_class = total_class

    con = get_connection()
    cur = con.cursor()
    cur.execute("""
      INSERT INTO attendance(enroll_id, total_class, attended_class)
      VALUES (%s,%s,%s)
      ON DUPLICATE KEY UPDATE total_class=VALUES(total_class),
                              attended_class=VALUES(attended_class)
    """, (enroll_id, total_class, attended_class))
    con.commit()
    cur.close(); con.close()

    pct = round((attended_class / total_class) * 100, 2) if total_class > 0 else 0.0
    return jsonify({"message":"Attendance saved", "attendance_percent": pct})

# ---------------- ADMIN DASHBOARD/ANALYTICS ----------------
@app.route("/admin/dashboard")
def admin_dashboard():
    if not require_role("admin"):
        return redirect("/login")
    return render_template("admin_dashboard.html", title="Admin Dashboard")

@app.route("/admin/analytics/grade-distribution")
def admin_grade_distribution():
    if not require_role("admin"):
        return jsonify({"error":"Unauthorized"}), 401

    con = get_connection()
    cur = con.cursor(dictionary=True)
    cur.execute("""
      SELECT letter_grade, COUNT(*) AS cnt
      FROM results
      WHERE is_published=1
      GROUP BY letter_grade
      ORDER BY cnt DESC
    """)
    rows = cur.fetchall()
    cur.close(); con.close()

    return jsonify({
        "labels":[r["letter_grade"] for r in rows],
        "values":[int(r["cnt"]) for r in rows]
    })

@app.route("/admin/analytics/course-difficulty")
def admin_course_difficulty():
    if not require_role("admin"):
        return jsonify({"error":"Unauthorized"}), 401

    con = get_connection()
    cur = con.cursor(dictionary=True)
    cur.execute("""
      SELECT c.code, c.title,
             AVG(r.total_percent) AS avg_percent,
             SUM(CASE WHEN r.letter_grade='F' THEN 1 ELSE 0 END) AS fail_count,
             COUNT(*) AS total_count
      FROM results r
      JOIN enrollments e ON r.enroll_id=e.enroll_id
      JOIN courses c ON e.course_id=c.course_id
      WHERE r.is_published=1
      GROUP BY c.course_id
      HAVING total_count > 0
      ORDER BY (fail_count/total_count) DESC, avg_percent ASC
      LIMIT 10
    """)
    rows = cur.fetchall()
    for r in rows:
        total = int(r["total_count"])
        fail = int(r["fail_count"])
        r["avg_percent"] = float(r["avg_percent"] or 0)
        r["fail_rate"] = round((fail/total)*100, 2) if total else 0
    cur.close(); con.close()
    return jsonify(rows)

@app.route("/admin/analytics/top-students")
def admin_top_students():
    if not require_role("admin"):
        return jsonify({"error":"Unauthorized"}), 401

    con = get_connection()
    cur = con.cursor(dictionary=True)
    cur.execute("""
      SELECT u.name, u.email,
             AVG(r.grade_point) AS avg_gp,
             COUNT(*) AS courses_count
      FROM results r
      JOIN enrollments e ON r.enroll_id=e.enroll_id
      JOIN students s ON e.student_id=s.student_id
      JOIN users u ON s.user_id=u.user_id
      WHERE r.is_published=1
      GROUP BY u.user_id
      HAVING courses_count >= 2
      ORDER BY avg_gp DESC, courses_count DESC
      LIMIT 10
    """)
    rows = cur.fetchall()
    for r in rows:
        r["avg_gp"] = round(float(r["avg_gp"] or 0), 3)
        r["courses_count"] = int(r["courses_count"])
    cur.close(); con.close()
    return jsonify(rows)

@app.route("/admin/analytics/at-risk")
def admin_at_risk():
    if not require_role("admin"):
        return jsonify({"error":"Unauthorized"}), 401

    con = get_connection()
    cur = con.cursor(dictionary=True)
    cur.execute("""
      SELECT u.name, u.email,
             AVG(r.grade_point) AS avg_gp,
             SUM(CASE WHEN r.letter_grade='F' THEN 1 ELSE 0 END) AS f_count,
             COUNT(*) AS courses_count
      FROM results r
      JOIN enrollments e ON r.enroll_id=e.enroll_id
      JOIN students s ON e.student_id=s.student_id
      JOIN users u ON s.user_id=u.user_id
      WHERE r.is_published=1
      GROUP BY u.user_id
      HAVING (AVG(r.grade_point) < 2.50) OR (SUM(CASE WHEN r.letter_grade='F' THEN 1 ELSE 0 END) >= 2)
      ORDER BY avg_gp ASC, f_count DESC
      LIMIT 15
    """)
    rows = cur.fetchall()
    for r in rows:
        r["avg_gp"] = round(float(r["avg_gp"] or 0), 3)
        r["f_count"] = int(r["f_count"] or 0)
        r["courses_count"] = int(r["courses_count"])
    cur.close(); con.close()
    return jsonify(rows)

# ---------------- ADMIN ASSIGN COURSE ----------------
@app.route("/admin/assign-course")
def admin_assign_course_page():
    if not require_role("admin"):
        return redirect("/login")
    return render_template("admin_assign_course.html", title="Assign Course")

@app.route("/admin/meta")
def admin_meta():
    if not require_role("admin"):
        return jsonify({"error":"Unauthorized"}), 401

    con = get_connection()
    cur = con.cursor(dictionary=True)

    cur.execute("""
      SELECT t.teacher_id, u.name, u.email, t.dept, t.designation
      FROM teachers t JOIN users u ON t.user_id=u.user_id
      ORDER BY u.name
    """)
    teachers = cur.fetchall()

    cur.execute("SELECT course_id, code, title FROM courses ORDER BY code")
    courses = cur.fetchall()

    cur.execute("SELECT semester_id, name, year FROM semesters ORDER BY year, semester_id")
    semesters = cur.fetchall()

    cur.close(); con.close()
    return jsonify({"teachers":teachers, "courses":courses, "semesters":semesters})

@app.route("/admin/assign-course", methods=["POST"])
def admin_assign_course():
    if not require_role("admin"):
        return jsonify({"error":"Unauthorized"}), 401

    data = request.get_json(force=True)
    teacher_id = int(data["teacher_id"])
    course_id = int(data["course_id"])
    semester_id = int(data["semester_id"])
    section = (data.get("section") or "").strip() or None

    con = get_connection()
    cur = con.cursor()
    cur.execute("""
      INSERT INTO course_teachers(teacher_id, course_id, semester_id, section)
      VALUES (%s,%s,%s,%s)
      ON DUPLICATE KEY UPDATE section=VALUES(section)
    """, (teacher_id, course_id, semester_id, section))
    con.commit()
    cur.close(); con.close()
    return jsonify({"message":"Course assigned to teacher"})

# ---------------- ADMIN PUBLISH ----------------
@app.route("/admin/publish")
def admin_publish_page():
    if not require_role("admin"):
        return redirect("/login")
    return render_template("admin_publish.html", title="Publish Results")

@app.route("/admin/drafts")
def admin_drafts():
    if not require_role("admin"):
        return jsonify({"error":"Unauthorized"}), 401

    con = get_connection()
    cur = con.cursor(dictionary=True)
    cur.execute("""
      SELECT r.result_id, r.total_percent, r.letter_grade, r.grade_point, r.is_published,
             u.name AS student_name, u.email,
             c.code, c.title, sem.name AS semester, sem.year
      FROM results r
      JOIN enrollments e ON r.enroll_id=e.enroll_id
      JOIN students s ON e.student_id=s.student_id
      JOIN users u ON s.user_id=u.user_id
      JOIN courses c ON e.course_id=c.course_id
      JOIN semesters sem ON e.semester_id=sem.semester_id
      WHERE r.is_published=0
      ORDER BY sem.year, sem.semester_id, c.code, u.name
      LIMIT 200
    """)
    rows = cur.fetchall()
    cur.close(); con.close()
    return jsonify(rows)

@app.route("/admin/publish-result", methods=["POST"])
def admin_publish_result():
    if not require_role("admin"):
        return jsonify({"error":"Unauthorized"}), 401

    data = request.get_json(force=True)
    result_id = int(data["result_id"])
    publish = 1 if data.get("publish", True) else 0

    con = get_connection()
    cur = con.cursor()
    cur.execute("UPDATE results SET is_published=%s WHERE result_id=%s", (publish, result_id))
    con.commit()
    cur.close(); con.close()
    return jsonify({"message":"Published" if publish else "Unpublished"})

# ---------------- ADMIN CRUD COURSES ----------------
@app.route("/admin/courses")
def admin_courses_page():
    if not require_role("admin"):
        return redirect("/login")
    return render_template("admin_courses.html", title="Manage Courses")

@app.route("/admin/api/courses", methods=["GET"])
def admin_api_courses_list():
    if not require_role("admin"):
        return jsonify({"error":"Unauthorized"}), 401

    q = (request.args.get("q") or "").strip()
    con = get_connection()
    cur = con.cursor(dictionary=True)

    if q:
        like = f"%{q}%"
        cur.execute("""
          SELECT course_id, code, title, credit
          FROM courses
          WHERE code LIKE %s OR title LIKE %s
          ORDER BY code
        """, (like, like))
    else:
        cur.execute("SELECT course_id, code, title, credit FROM courses ORDER BY code")

    rows = cur.fetchall()
    cur.close(); con.close()
    return jsonify(rows)

@app.route("/admin/api/courses", methods=["POST"])
def admin_api_courses_create():
    if not require_role("admin"):
        return jsonify({"error":"Unauthorized"}), 401

    data = request.get_json(force=True)
    code = (data.get("code") or "").strip()
    title = (data.get("title") or "").strip()
    credit = float(data.get("credit") or 3.0)

    if not code or not title:
        return jsonify({"error":"code and title required"}), 400

    con = get_connection()
    cur = con.cursor()
    try:
        cur.execute("INSERT INTO courses(code, title, credit) VALUES (%s,%s,%s)", (code, title, credit))
        con.commit()
    except Exception:
        con.rollback()
        cur.close(); con.close()
        return jsonify({"error":"Course code must be unique"}), 400

    cur.close(); con.close()
    return jsonify({"message":"Course added"})

@app.route("/admin/api/courses/<int:course_id>", methods=["PUT"])
def admin_api_courses_update(course_id):
    if not require_role("admin"):
        return jsonify({"error":"Unauthorized"}), 401

    data = request.get_json(force=True)
    code = (data.get("code") or "").strip()
    title = (data.get("title") or "").strip()
    credit = float(data.get("credit") or 3.0)

    if not code or not title:
        return jsonify({"error":"code and title required"}), 400

    con = get_connection()
    cur = con.cursor()
    try:
        cur.execute("UPDATE courses SET code=%s, title=%s, credit=%s WHERE course_id=%s",
                    (code, title, credit, course_id))
        con.commit()
    except Exception:
        con.rollback()
        cur.close(); con.close()
        return jsonify({"error":"Update failed (duplicate code?)"}), 400

    cur.close(); con.close()
    return jsonify({"message":"Course updated"})

@app.route("/admin/api/courses/<int:course_id>", methods=["DELETE"])
def admin_api_courses_delete(course_id):
    if not require_role("admin"):
        return jsonify({"error":"Unauthorized"}), 401

    con = get_connection()
    cur = con.cursor()
    cur.execute("DELETE FROM courses WHERE course_id=%s", (course_id,))
    con.commit()
    cur.close(); con.close()
    return jsonify({"message":"Course deleted"})

# ---------------- ADMIN CRUD STUDENTS ----------------
@app.route("/admin/students")
def admin_students_page():
    if not require_role("admin"):
        return redirect("/login")
    return render_template("admin_students.html", title="Manage Students")

@app.route("/admin/api/students", methods=["GET"])
def admin_api_students_list():
    if not require_role("admin"):
        return jsonify({"error":"Unauthorized"}), 401

    q = (request.args.get("q") or "").strip()
    con = get_connection()
    cur = con.cursor(dictionary=True)

    if q:
        like = f"%{q}%"
        cur.execute("""
          SELECT s.student_id, u.user_id, u.name, u.email, s.dept, s.batch, s.section
          FROM students s JOIN users u ON s.user_id=u.user_id
          WHERE u.name LIKE %s OR u.email LIKE %s OR s.dept LIKE %s OR s.batch LIKE %s
          ORDER BY u.name
        """, (like, like, like, like))
    else:
        cur.execute("""
          SELECT s.student_id, u.user_id, u.name, u.email, s.dept, s.batch, s.section
          FROM students s JOIN users u ON s.user_id=u.user_id
          ORDER BY u.name
        """)
    rows = cur.fetchall()
    cur.close(); con.close()
    return jsonify(rows)

@app.route("/admin/api/students", methods=["POST"])
def admin_api_students_create():
    if not require_role("admin"):
        return jsonify({"error":"Unauthorized"}), 401

    data = request.get_json(force=True)
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip()
    dept = (data.get("dept") or "").strip()
    batch = (data.get("batch") or "").strip()
    section = (data.get("section") or "").strip()

    if not name or not email:
        return jsonify({"error":"name and email required"}), 400

    pw = data.get("password") or "student123"
    pw_hash = generate_password_hash(pw)

    con = get_connection()
    cur = con.cursor()
    try:
        cur.execute("INSERT INTO users(name, email, password_hash, role) VALUES (%s,%s,%s,'student')",
                    (name, email, pw_hash))
        user_id = cur.lastrowid

        cur.execute("INSERT INTO students(user_id, dept, batch, section) VALUES (%s,%s,%s,%s)",
                    (user_id, dept, batch, section))
        con.commit()
    except Exception:
        con.rollback()
        cur.close(); con.close()
        return jsonify({"error":"Email must be unique"}), 400

    cur.close(); con.close()
    return jsonify({"message":"Student added (default password: student123)"})

@app.route("/admin/api/students/<int:student_id>", methods=["PUT"])
def admin_api_students_update(student_id):
    if not require_role("admin"):
        return jsonify({"error":"Unauthorized"}), 401

    data = request.get_json(force=True)
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip()
    dept = (data.get("dept") or "").strip()
    batch = (data.get("batch") or "").strip()
    section = (data.get("section") or "").strip()

    if not name or not email:
        return jsonify({"error":"name and email required"}), 400

    con = get_connection()
    cur = con.cursor(dictionary=True)
    cur.execute("SELECT user_id FROM students WHERE student_id=%s", (student_id,))
    s = cur.fetchone()
    if not s:
        cur.close(); con.close()
        return jsonify({"error":"Student not found"}), 404

    user_id = s["user_id"]

    try:
        cur2 = con.cursor()
        cur2.execute("UPDATE users SET name=%s, email=%s WHERE user_id=%s", (name, email, user_id))
        cur2.execute("UPDATE students SET dept=%s, batch=%s, section=%s WHERE student_id=%s",
                     (dept, batch, section, student_id))
        con.commit()
        cur2.close()
    except Exception:
        con.rollback()
        cur.close(); con.close()
        return jsonify({"error":"Update failed (duplicate email?)"}), 400

    cur.close(); con.close()
    return jsonify({"message":"Student updated"})

@app.route("/admin/api/students/<int:student_id>", methods=["DELETE"])
def admin_api_students_delete(student_id):
    if not require_role("admin"):
        return jsonify({"error":"Unauthorized"}), 401

    con = get_connection()
    cur = con.cursor(dictionary=True)
    cur.execute("SELECT user_id FROM students WHERE student_id=%s", (student_id,))
    s = cur.fetchone()
    if not s:
        cur.close(); con.close()
        return jsonify({"error":"Student not found"}), 404

    user_id = s["user_id"]
    cur2 = con.cursor()
    cur2.execute("DELETE FROM users WHERE user_id=%s", (user_id,))
    con.commit()
    cur2.close()
    cur.close(); con.close()
    return jsonify({"message":"Student deleted"})

# ---------------- ADMIN ENROLLMENTS ----------------
@app.route("/admin/enrollments")
def admin_enrollments_page():
    if not require_role("admin"):
        return redirect("/login")
    return render_template("admin_enrollments.html", title="Enrollments")

@app.route("/admin/enroll-meta")
def admin_enroll_meta():
    if not require_role("admin"):
        return jsonify({"error":"Unauthorized"}), 401

    con = get_connection()
    cur = con.cursor(dictionary=True)

    cur.execute("""
      SELECT s.student_id, u.name, u.email, s.dept, s.batch, s.section
      FROM students s JOIN users u ON s.user_id=u.user_id
      ORDER BY u.name
      LIMIT 500
    """)
    students = cur.fetchall()

    cur.execute("SELECT course_id, code, title, credit FROM courses ORDER BY code")
    courses = cur.fetchall()

    cur.execute("SELECT semester_id, name, year FROM semesters ORDER BY year, semester_id")
    semesters = cur.fetchall()

    cur.close(); con.close()
    return jsonify({"students":students, "courses":courses, "semesters":semesters})

@app.route("/admin/api/enroll", methods=["POST"])
def admin_api_enroll():
    if not require_role("admin"):
        return jsonify({"error":"Unauthorized"}), 401

    data = request.get_json(force=True)
    student_id = int(data["student_id"])
    course_id = int(data["course_id"])
    semester_id = int(data["semester_id"])

    con = get_connection()
    cur = con.cursor()

    cur.execute("""
      INSERT INTO enrollments(student_id, course_id, semester_id)
      VALUES (%s,%s,%s)
      ON DUPLICATE KEY UPDATE student_id=student_id
    """, (student_id, course_id, semester_id))

    cur2 = con.cursor(dictionary=True)
    cur2.execute("""
      SELECT enroll_id FROM enrollments
      WHERE student_id=%s AND course_id=%s AND semester_id=%s
      LIMIT 1
    """, (student_id, course_id, semester_id))
    row = cur2.fetchone()
    enroll_id = row["enroll_id"]

    cur.execute("""
      INSERT INTO attendance(enroll_id, total_class, attended_class)
      VALUES (%s,0,0)
      ON DUPLICATE KEY UPDATE enroll_id=enroll_id
    """, (enroll_id,))
    con.commit()

    cur2.close()
    cur.close(); con.close()
    return jsonify({"message":"Student enrolled + attendance initialized", "enroll_id": enroll_id})

@app.route("/admin/api/enrollments", methods=["GET"])
def admin_api_enrollments_list():
    if not require_role("admin"):
        return jsonify({"error":"Unauthorized"}), 401

    con = get_connection()
    cur = con.cursor(dictionary=True)
    cur.execute("""
      SELECT e.enroll_id,
             u.name AS student_name, u.email,
             s.dept, s.batch, s.section,
             c.code, c.title,
             sem.name AS semester, sem.year
      FROM enrollments e
      JOIN students s ON e.student_id=s.student_id
      JOIN users u ON s.user_id=u.user_id
      JOIN courses c ON e.course_id=c.course_id
      JOIN semesters sem ON e.semester_id=sem.semester_id
      ORDER BY sem.year, sem.semester_id, c.code, u.name
      LIMIT 500
    """)
    rows = cur.fetchall()
    cur.close(); con.close()
    return jsonify(rows)

@app.route("/admin/api/enrollments/<int:enroll_id>", methods=["DELETE"])
def admin_api_enrollments_delete(enroll_id):
    if not require_role("admin"):
        return jsonify({"error":"Unauthorized"}), 401

    con = get_connection()
    cur = con.cursor()
    cur.execute("DELETE FROM enrollments WHERE enroll_id=%s", (enroll_id,))
    con.commit()
    cur.close(); con.close()
    return jsonify({"message":"Enrollment deleted"})

# ---------------- ADMIN EXPORT CSV ----------------
@app.route("/admin/export")
def admin_export_page():
    if not require_role("admin"):
        return redirect("/login")
    return render_template("admin_export.html", title="Export CSV")

@app.route("/admin/export/meta")
def admin_export_meta():
    if not require_role("admin"):
        return jsonify({"error":"Unauthorized"}), 401

    con = get_connection()
    cur = con.cursor(dictionary=True)
    cur.execute("SELECT semester_id, name, year FROM semesters ORDER BY year, semester_id")
    semesters = cur.fetchall()
    cur.execute("SELECT course_id, code, title FROM courses ORDER BY code")
    courses = cur.fetchall()
    cur.close(); con.close()
    return jsonify({"semesters":semesters, "courses":courses})

@app.route("/admin/export/results.csv")
def admin_export_results_csv():
    if not require_role("admin"):
        return redirect("/login")

    semester_id = (request.args.get("semester_id") or "").strip()
    course_id = (request.args.get("course_id") or "").strip()
    q = (request.args.get("q") or "").strip()

    where = ["r.is_published = 1"]
    params = []

    if semester_id.isdigit():
        where.append("e.semester_id = %s")
        params.append(int(semester_id))
    if course_id.isdigit():
        where.append("e.course_id = %s")
        params.append(int(course_id))
    if q:
        where.append("(u.name LIKE %s OR u.email LIKE %s)")
        like = f"%{q}%"
        params.extend([like, like])

    where_sql = " AND ".join(where)

    con = get_connection()
    cur = con.cursor(dictionary=True)
    cur.execute(f"""
      SELECT u.name AS student_name, u.email AS student_email,
             s.dept, s.batch, s.section,
             c.code AS course_code, c.title AS course_title, c.credit,
             sem.name AS semester, sem.year,
             r.total_percent, r.letter_grade, r.grade_point, r.published_at
      FROM results r
      JOIN enrollments e ON r.enroll_id=e.enroll_id
      JOIN students s ON e.student_id=s.student_id
      JOIN users u ON s.user_id=u.user_id
      JOIN courses c ON e.course_id=c.course_id
      JOIN semesters sem ON e.semester_id=sem.semester_id
      WHERE {where_sql}
      ORDER BY sem.year, sem.semester_id, c.code, u.name
    """, tuple(params))
    rows = cur.fetchall()
    cur.close(); con.close()

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "student_name","student_email","dept","batch","section",
        "course_code","course_title","credit",
        "semester","year","total_percent","letter_grade","grade_point","published_at"
    ])
    for r in rows:
        writer.writerow([
            r["student_name"], r["student_email"], r["dept"], r["batch"], r["section"],
            r["course_code"], r["course_title"], r["credit"],
            r["semester"], r["year"],
            r["total_percent"], r["letter_grade"], r["grade_point"], r["published_at"]
        ])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition":"attachment; filename=published_results.csv"}
    )

# ---------------- ADMIN RESET PASSWORD ----------------
@app.route("/admin/reset-password")
def admin_reset_password_page():
    if not require_role("admin"):
        return redirect("/login")
    return render_template("admin_reset_password.html", title="Reset Password")

@app.route("/admin/api/reset-password", methods=["POST"])
def admin_reset_password():
    if not require_role("admin"):
        return jsonify({"error":"Unauthorized"}), 401

    data = request.get_json(force=True)
    email = (data.get("email") or "").strip()
    new_password = (data.get("new_password") or "").strip()

    if not email or not new_password:
        return jsonify({"error":"email and new_password required"}), 400
    if len(new_password) < 6:
        return jsonify({"error":"Password must be at least 6 characters"}), 400

    pw_hash = generate_password_hash(new_password)

    con = get_connection()
    cur = con.cursor()
    cur.execute("UPDATE users SET password_hash=%s WHERE email=%s", (pw_hash, email))
    con.commit()
    updated = cur.rowcount
    cur.close(); con.close()

    if updated == 0:
        return jsonify({"error":"User not found"}), 404
    return jsonify({"message":f"Password reset successful for {email}"})

if __name__ == "__main__":
    app.run(debug=True)
