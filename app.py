from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from extensions import db
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = "emp-development-secret-key"

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///examination.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False    

db.init_app(app)

@app.route("/")
def home():
    return render_template("home.html")


@app.route("/register/student", methods=["GET", "POST"])
def student_register():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        roll_number = request.form["roll_number"]
        department = request.form["department"]
        contact = request.form["contact"]

        if User.query.filter_by(email=email).first():
            flash("Email already registered.")
            return redirect(url_for("student_register"))

        if Student.query.filter_by(roll_number=roll_number).first():
            flash("Roll number already registered.")
            return redirect(url_for("student_register"))

        user = User(
            full_name=name,
            email=email,
            password=generate_password_hash(password),
            role="student"
        )

        db.session.add(user)
        db.session.flush()

        student = Student(
            user_id=user.id,
            roll_number=roll_number,
            department=department,
            contact=contact
        )

        db.session.add(student)
        db.session.commit()

        flash("Student registration successful. Please log in.")
        return redirect(url_for("login"))

    return render_template("student_register.html")


@app.route("/register/examiner", methods=["GET", "POST"])
def examiner_register():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        department = request.form["department"]
        contact = request.form["contact"]

        if User.query.filter_by(email=email).first():
            flash("Email already registered.")
            return redirect(url_for("examiner_register"))

        user = User(
            full_name=name,
            email=email,
            password=generate_password_hash(password),
            role="examiner"
        )

        db.session.add(user)
        db.session.flush()

        examiner = Examiner(
            user_id=user.id,
            department=department,
            contact=contact,
            status="pending"
        )

        db.session.add(examiner)
        db.session.commit()

        flash("Registration successful. Wait for Admin approval.")
        return redirect(url_for("login"))

    return render_template("examiner_register.html")

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):

            if user.role == "examiner":
                examiner = Examiner.query.filter_by(user_id=user.id).first()

                if examiner.status != "approved":
                    flash("Your account is waiting for Admin approval.")
                    return redirect(url_for("login"))

            session["user_id"] = user.id
            session["role"] = user.role

            if user.role == "admin":
                return redirect(url_for("admin_dashboard"))

            elif user.role == "student":
                return redirect(url_for("student_dashboard"))

            elif user.role == "examiner":
                return redirect(url_for("examiner_dashboard"))

        flash("Invalid email or password.")
        return redirect(url_for("login"))

    return render_template("login.html")

@app.route("/admin/dashboard")
def admin_dashboard():
    if "user_id" not in session or session.get("role") != "admin":
        return redirect(url_for("login"))

    return render_template("admin_dashboard.html")


@app.route("/examiner/dashboard")
def examiner_dashboard():
    if "user_id" not in session or session.get("role") != "examiner":
        return redirect(url_for("login"))

    return render_template("examiner_dashboard.html")


@app.route("/student/dashboard")
def student_dashboard():
    if "user_id" not in session or session.get("role") != "student":
        return redirect(url_for("login"))

    return render_template("student_dashboard.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out successfully.")
    return redirect(url_for("login"))

@app.route("/admin/examiners")
def manage_examiners():

    if "user_id" not in session or session.get("role") != "admin":
        return redirect(url_for("login"))

    pending_examiners = Examiner.query.filter_by(
        status="pending"
    ).all()

    return render_template(
        "manage_examiners.html",
        examiners=pending_examiners
    )

@app.route("/admin/examiners/<int:examiner_id>/approve", methods=["POST"])
def approve_examiner(examiner_id):
    if "user_id" not in session or session.get("role") != "admin":
        return redirect(url_for("login"))

    examiner = db.get_or_404(Examiner, examiner_id)
    examiner.status = "approved"

    db.session.commit()

    flash("Examiner approved successfully.")
    return redirect(url_for("manage_examiners"))

if __name__ == "__main__":
    with app.app_context():
        from models import *
        db.create_all()
        print("Database tables created successfully.")
        print("All models and relationships loaded successfully.")


    app.run(debug=True)