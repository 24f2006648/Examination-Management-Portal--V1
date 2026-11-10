from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from extensions import db
from werkzeug.security import generate_password_hash, check_password_hash
from models import *
    

from datetime import datetime

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

    stats = {
        "students": Student.query.count(),
        "examiners": Examiner.query.filter_by(status="approved").count(),
        "pending_examiners": Examiner.query.filter_by(status="pending").count(),
        "courses": Course.query.count(),
        "examinations": Examination.query.count(),
        "slots": ExaminationSlot.query.count(),
        "bookings": Booking.query.filter_by(status="Booked").count()
    }

    return render_template("admin_dashboard.html", stats=stats)


@app.route("/examiner/dashboard")
def examiner_dashboard():

    if "user_id" not in session or session.get("role") != "examiner":
        return redirect(url_for("login"))

    examiner = Examiner.query.filter_by(
        user_id=session["user_id"]
    ).first()

    if not examiner or examiner.status != "approved":
        session.clear()
        flash("Your examiner account is not active.")
        return redirect(url_for("login"))

    assignments = ExaminerAssignment.query.filter_by(
        examiner_id=examiner.id
    ).all()

    assigned_slots = ExaminationSlot.query.filter_by(
        examiner_id=examiner.id
    ).all()

    stats = {
        "assigned_exams": len(assignments),
        "total_slots": len(assigned_slots),
        "available_slots": ExaminationSlot.query.filter_by(
            examiner_id=examiner.id,
            status="Available"
        ).count(),
        "total_bookings": Booking.query.join(
            ExaminationSlot
        ).filter(
            ExaminationSlot.examiner_id == examiner.id,
            Booking.status == "Booked"
        ).count()
    }

    return render_template(
        "examiner_dashboard.html",
        examiner=examiner,
        assignments=assignments,
        assigned_slots=assigned_slots,
        stats=stats
    )


@app.route("/student/dashboard", methods=["GET", "POST"])
def student_dashboard():
    if "user_id" not in session or session.get("role") != "student":
        return redirect(url_for("login"))

    student = Student.query.filter_by(
        user_id=session["user_id"]
    ).first()

    if not student:
        session.clear()
        flash("Student profile not found.")
        return redirect(url_for("login"))

    def booking_allowed(exam):
        now = datetime.now()

        return (
            exam.booking_open
            and exam.booking_start is not None
            and exam.booking_end is not None
            and exam.booking_start <= now <= exam.booking_end
        )

    if request.method == "POST":
        action = request.form.get("action")

        # BOOK AN EXAMINATION SLOT
        if action == "book":
            slot = db.get_or_404(
                ExaminationSlot,
                int(request.form["slot_id"])
            )

            exam = slot.examination

            existing_booking = Booking.query.join(
                ExaminationSlot
            ).filter(
                Booking.student_id == student.id,
                ExaminationSlot.exam_id == exam.id,
                Booking.status == "Booked"
            ).first()

            if existing_booking:
                flash("You already have an active booking for this examination.")

            elif not booking_allowed(exam):
                flash("Booking is closed or outside the allowed timeline.")

            elif slot.status != "Available" or slot.available_seats <= 0:
                flash("This slot is full or unavailable.")

            elif datetime.combine(slot.date, slot.start_time) <= datetime.now():
                flash("You cannot book a slot that has already started.")

            else:
                booking = Booking(
                    student_id=student.id,
                    slot_id=slot.id,
                    status="Booked"
                )

                slot.available_seats -= 1

                if slot.available_seats == 0:
                    slot.status = "Full"

                db.session.add(booking)
                db.session.commit()

                flash("Examination slot booked successfully.")

        # CANCEL AN EXISTING BOOKING
        elif action == "cancel":
            booking = db.get_or_404(
                Booking,
                int(request.form["booking_id"])
            )

            if booking.student_id != student.id:
                flash("You cannot cancel another student's booking.")

            elif booking.status != "Booked":
                flash("This booking is not active.")

            elif (
                booking.slot.examination.booking_end is None
                or datetime.now() > booking.slot.examination.booking_end
            ):
                flash("The cancellation deadline has passed.")

            else:
                slot = booking.slot

                booking.status = "Cancelled"
                slot.available_seats += 1

                if slot.available_seats > slot.capacity:
                    slot.available_seats = slot.capacity

                if slot.available_seats > 0:
                    slot.status = "Available"

                db.session.commit()

                flash("Booking cancelled successfully.")

        return redirect(url_for("student_dashboard"))

    # SEARCH AND FILTER EXAMINATIONS
    search = request.args.get("search", "").strip()
    selected_type = request.args.get("exam_type", "")
    selected_course = request.args.get("course_id", type=int)

    exam_query = Examination.query.join(Course)

    if search:
        search_text = f"%{search}%"
        exam_query = exam_query.filter(
            (Examination.name.ilike(search_text))
            | (Course.name.ilike(search_text))
            | (Course.code.ilike(search_text))
        )

    if selected_type:
        exam_query = exam_query.filter(
            Examination.exam_type == selected_type
        )

    if selected_course:
        exam_query = exam_query.filter(
            Examination.course_id == selected_course
        )

    examinations = exam_query.order_by(
        Examination.id.desc()
    ).all()

    # SHOW ONLY FUTURE SLOTS IN THE EXAMINATION LIST
    for exam in examinations:
        exam.available_slots = [
            slot for slot in exam.slots
            if slot.status == "Available"
            and slot.available_seats > 0
            and datetime.combine(
                slot.date, slot.start_time
            ) > datetime.now()
        ]

    courses = Course.query.filter_by(status="active").all()
    exam_types = db.session.query(
        Examination.exam_type
    ).distinct().all()

    # ALL BOOKINGS BELONGING TO THIS STUDENT
    student_bookings = Booking.query.filter_by(
        student_id=student.id
    ).order_by(
        Booking.booking_date.desc()
    ).all()

    upcoming_bookings = [
        booking for booking in student_bookings
        if booking.status == "Booked"
        and datetime.combine(
            booking.slot.date,
            booking.slot.start_time
        ) > datetime.now()
    ]

    return render_template(
        "student_dashboard.html",
        student=student,
        examinations=examinations,
        courses=courses,
        exam_types=exam_types,
        student_bookings=student_bookings,
        upcoming_bookings=upcoming_bookings,
        search=search,
        selected_type=selected_type,
        selected_course=selected_course
    )

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

@app.route("/admin/courses", methods=["GET", "POST"])
def manage_courses():
    if "user_id" not in session or session.get("role") != "admin":
        return redirect(url_for("login"))

    if request.method == "POST":
        action = request.form["action"]

        if action == "add":
            course = Course(
                name=request.form["name"],
                code=request.form["code"],
                description=request.form["description"]
            )

            if Course.query.filter_by(code=course.code).first():
                flash("Course code already exists.")
            else:
                db.session.add(course)
                db.session.commit()
                flash("Course added successfully.")

        elif action == "edit":
            course = db.get_or_404(Course, request.form["course_id"])

            existing = Course.query.filter(
                Course.code == request.form["code"],
                Course.id != course.id
            ).first()

            if existing:
                flash("Course code already exists.")
            else:
                course.name = request.form["name"]
                course.code = request.form["code"]
                course.description = request.form["description"]
                db.session.commit()
                flash("Course updated successfully.")

        elif action == "delete":
            course = db.get_or_404(Course, request.form["course_id"])

            if course.examinations:
                flash("Cannot delete a course with examinations.")
            else:
                db.session.delete(course)
                db.session.commit()
                flash("Course deleted successfully.")

        return redirect(url_for("manage_courses"))

    courses = Course.query.all()

    edit_id = request.args.get("edit_id", type=int)
    edit_course = db.session.get(Course, edit_id) if edit_id else None

    return render_template(
        "manage_courses.html",
        courses=courses,
        edit_course=edit_course
    )

@app.route("/admin/examinations", methods=["GET", "POST"])
def manage_examinations():
    if "user_id" not in session or session.get("role") != "admin":
        return redirect(url_for("login"))

    if request.method == "POST":
        action = request.form["action"]

        # ADD EXAMINATION
        if action == "add":
            exam = Examination(
                course_id=int(request.form["course_id"]),
                name=request.form["name"],
                exam_type=request.form["exam_type"],
                duration=int(request.form["duration"]),
                max_marks=int(request.form["max_marks"]),
                status="Draft"
            )

            db.session.add(exam)
            db.session.commit()
            flash("Examination added successfully.")

        # EDIT EXAMINATION
        elif action == "edit":
            exam = db.get_or_404(
                Examination, int(request.form["exam_id"])
            )

            exam.course_id = int(request.form["course_id"])
            exam.name = request.form["name"]
            exam.exam_type = request.form["exam_type"]
            exam.duration = int(request.form["duration"])
            exam.max_marks = int(request.form["max_marks"])

            db.session.commit()
            flash("Examination updated successfully.")

        # DELETE EXAMINATION
        elif action == "delete":
            exam = db.get_or_404(
                Examination, int(request.form["exam_id"])
            )

            if exam.slots or exam.rubrics:
                flash("Cannot delete an examination with existing slots or rubrics.")
            else:
                db.session.delete(exam)
                db.session.commit()
                flash("Examination deleted successfully.")

        return redirect(url_for("manage_examinations"))

    courses = Course.query.filter_by(status="active").all()
    examinations = Examination.query.all()

    edit_id = request.args.get("edit_id", type=int)
    edit_exam = db.session.get(Examination, edit_id) if edit_id else None

    return render_template(
        "manage_examinations.html",
        courses=courses,
        examinations=examinations,
        edit_exam=edit_exam
    ) 

@app.route("/admin/management", methods=["GET", "POST"])
def admin_management():
    if "user_id" not in session or session.get("role") != "admin":
        return redirect(url_for("login"))

    if request.method == "POST":
        action = request.form.get("action")

        # ADD RUBRIC
        if action == "add_rubric":
            rubric = ExaminationRubric(
                exam_id=int(request.form["exam_id"]),
                criterion_name=request.form["criterion_name"],
                max_marks=int(request.form["max_marks"]),
                weightage=float(request.form["weightage"]),
                description=request.form.get("description")
            )
            db.session.add(rubric)
            db.session.commit()
            flash("Rubric added successfully.")

        # DELETE RUBRIC
        elif action == "delete_rubric":
            rubric = db.get_or_404(
                ExaminationRubric, int(request.form["rubric_id"])
            )
            db.session.delete(rubric)
            db.session.commit()
            flash("Rubric deleted successfully.")

        # ACTIVATE / DEACTIVATE EXAMINER
        elif action in ["activate_examiner", "deactivate_examiner"]:
            examiner = db.get_or_404(
                Examiner, int(request.form["examiner_id"])
            )
            examiner.status = (
                "approved" if action == "activate_examiner" else "inactive"
            )
            db.session.commit()
            flash("Examiner status updated.")

        # UPDATE EXAMINATION TIMELINES
        elif action == "update_timeline":
            exam = db.get_or_404(
                Examination, int(request.form["exam_id"])
            )

            def parse_datetime(value):
                return datetime.strptime(value, "%Y-%m-%dT%H:%M") if value else None

            exam.slot_creation_start = parse_datetime(
                request.form.get("slot_creation_start")
            )
            exam.slot_creation_end = parse_datetime(
                request.form.get("slot_creation_end")
            )
            exam.booking_start = parse_datetime(
                request.form.get("booking_start")
            )
            exam.booking_end = parse_datetime(
                request.form.get("booking_end")
            )

            db.session.commit()
            flash("Examination timelines updated.")

        # OPEN / CLOSE SLOT CREATION
        elif action == "toggle_slots":
            exam = db.get_or_404(
                Examination, int(request.form["exam_id"])
            )
            exam.slot_creation_open = not exam.slot_creation_open
            db.session.commit()
            flash("Slot creation setting updated.")

        # OPEN / CLOSE STUDENT BOOKING
        elif action == "toggle_booking":
            exam = db.get_or_404(
                Examination, int(request.form["exam_id"])
            )
            exam.booking_open = not exam.booking_open
            db.session.commit()
            flash("Booking setting updated.")

        # CHANGE EXAMINER FOR A SLOT
        elif action == "change_examiner":
            slot = db.get_or_404(
                ExaminationSlot, int(request.form["slot_id"])
            )
            examiner = db.get_or_404(
                Examiner, int(request.form["examiner_id"])
            )

            if examiner.status != "approved":
                flash("Only approved examiners can be assigned.")
            else:
                slot.examiner_id = examiner.id
                db.session.commit()
                flash("Slot examiner changed successfully.")

        # RESCHEDULE A BOOKING
        elif action == "reschedule_booking":
            booking = db.get_or_404(
                Booking, int(request.form["booking_id"])
            )
            new_slot = db.get_or_404(
                ExaminationSlot, int(request.form["new_slot_id"])
            )
            old_slot = booking.slot

            if booking.status != "Booked":
                flash("Only active bookings can be rescheduled.")
            elif new_slot.exam_id != old_slot.exam_id:
                flash("Select a slot belonging to the same examination.")
            elif new_slot.status != "Available" or new_slot.available_seats <= 0:
                flash("The selected slot is not available.")
            else:
                old_slot.available_seats += 1
                if old_slot.available_seats > old_slot.capacity:
                    old_slot.available_seats = old_slot.capacity

                new_slot.available_seats -= 1
                if new_slot.available_seats == 0:
                    new_slot.status = "Full"

                booking.slot_id = new_slot.id

                if old_slot.available_seats > 0:
                    old_slot.status = "Available"

                db.session.commit()
                flash("Booking rescheduled successfully.")

        
        # ASSIGN EXAMINATION TO EXAMINER
        elif action == "assign_examiner":
            examiner = db.get_or_404(
                Examiner,
                int(request.form["examiner_id"])
            )

            exam = db.get_or_404(
                Examination,
                int(request.form["exam_id"])
            )

            existing = ExaminerAssignment.query.filter_by(
                examiner_id=examiner.id,
                exam_id=exam.id
            ).first()

            if examiner.status != "approved":
                flash("Only approved examiners can be assigned.")

            elif existing:
                flash("This examination is already assigned to this examiner.")

            else:
                assignment = ExaminerAssignment(
                    examiner_id=examiner.id,
                    exam_id=exam.id
                )

                db.session.add(assignment)
                db.session.commit()

                flash("Examination assigned successfully.")

        # REMOVE EXAMINER ASSIGNMENT
        elif action == "remove_assignment":
            assignment = db.get_or_404(
                ExaminerAssignment,
                int(request.form["assignment_id"])
            )

            # Do not remove an assignment if the examiner has slots
            existing_slots = ExaminationSlot.query.filter_by(
                examiner_id=assignment.examiner_id,
                exam_id=assignment.exam_id
            ).first()

            if existing_slots:
                flash("Cannot remove assignment while examination slots exist.")
            else:
                db.session.delete(assignment)
                db.session.commit()

                flash("Examiner assignment removed.")



        return redirect(url_for("admin_management"))

    exams = Examination.query.all()
    rubrics = ExaminationRubric.query.all()
    examiners = Examiner.query.all()
    assignments = ExaminerAssignment.query.all()
    slots = ExaminationSlot.query.all()
    bookings = Booking.query.all()

    return render_template(
        "admin_management.html",
        exams=exams,
        rubrics=rubrics,
        examiners=examiners,
        slots=slots,
        bookings=bookings,
        assignments=assignments
    )     


@app.route("/examiner/slots", methods=["GET", "POST"])
def manage_examiner_slots():

    if "user_id" not in session or session.get("role") != "examiner":
        return redirect(url_for("login"))

    examiner = Examiner.query.filter_by(
        user_id=session["user_id"]
    ).first()

    if not examiner or examiner.status != "approved":
        session.clear()
        flash("Your examiner account is not active.")
        return redirect(url_for("login"))

    def booking_has_started(exam):
        now = datetime.now()

        return (
            exam.booking_open
            or (
                exam.booking_start is not None
                and now >= exam.booking_start
            )
        )

    def slot_creation_allowed(exam):
        now = datetime.now()

        return (
            exam.slot_creation_open
            and exam.slot_creation_start is not None
            and exam.slot_creation_end is not None
            and exam.slot_creation_start <= now <= exam.slot_creation_end
        )

    def get_slot_values():
        slot_date = datetime.strptime(
            request.form["date"], "%Y-%m-%d"
        ).date()

        start_time = datetime.strptime(
            request.form["start_time"], "%H:%M"
        ).time()

        end_time = datetime.strptime(
            request.form["end_time"], "%H:%M"
        ).time()

        capacity = int(request.form["capacity"])

        if end_time <= start_time:
            raise ValueError("End time must be later than start time.")

        if capacity <= 0:
            raise ValueError("Capacity must be greater than zero.")

        if datetime.combine(slot_date, start_time) <= datetime.now():
            raise ValueError("Slot must be scheduled in the future.")

        return slot_date, start_time, end_time, capacity

    if request.method == "POST":

        action = request.form.get("action")

        # CREATE SLOT
        if action == "add":

            exam = db.get_or_404(
                Examination,
                int(request.form["exam_id"])
            )

            assignment = ExaminerAssignment.query.filter_by(
                examiner_id=examiner.id,
                exam_id=exam.id
            ).first()

            if not assignment:
                flash("You are not assigned to this examination.")

            elif not slot_creation_allowed(exam):
                flash("Slot creation is currently closed or outside the allowed timeline.")

            else:
                try:
                    slot_date, start_time, end_time, capacity = get_slot_values()

                    overlapping_slot = ExaminationSlot.query.filter(
                        ExaminationSlot.examiner_id == examiner.id,
                        ExaminationSlot.date == slot_date,
                        ExaminationSlot.start_time < end_time,
                        ExaminationSlot.end_time > start_time
                    ).first()

                    if overlapping_slot:
                        flash("You already have an overlapping slot at this time.")

                    else:
                        slot = ExaminationSlot(
                            exam_id=exam.id,
                            examiner_id=examiner.id,
                            date=slot_date,
                            start_time=start_time,
                            end_time=end_time,
                            capacity=capacity,
                            available_seats=capacity,
                            status="Available"
                        )

                        db.session.add(slot)
                        db.session.commit()

                        flash("Examination slot created successfully.")

                except ValueError as error:
                    flash(str(error))

        # EDIT SLOT
        elif action == "edit":

            slot = db.get_or_404(
                ExaminationSlot,
                int(request.form["slot_id"])
            )

            exam = slot.examination

            if slot.examiner_id != examiner.id:
                flash("You cannot edit another examiner's slot.")

            elif booking_has_started(exam):
                flash("Slots cannot be edited after booking begins.")

            elif slot.bookings:
                flash("Slots with existing bookings cannot be edited.")

            else:
                try:
                    slot_date, start_time, end_time, capacity = get_slot_values()

                    overlapping_slot = ExaminationSlot.query.filter(
                        ExaminationSlot.examiner_id == examiner.id,
                        ExaminationSlot.date == slot_date,
                        ExaminationSlot.start_time < end_time,
                        ExaminationSlot.end_time > start_time,
                        ExaminationSlot.id != slot.id
                    ).first()

                    if overlapping_slot:
                        flash("You already have an overlapping slot at this time.")

                    else:
                        slot.date = slot_date
                        slot.start_time = start_time
                        slot.end_time = end_time
                        slot.capacity = capacity
                        slot.available_seats = capacity
                        slot.status = "Available"

                        db.session.commit()

                        flash("Examination slot updated successfully.")

                except ValueError as error:
                    flash(str(error))

        # DELETE SLOT
        elif action == "delete":

            slot = db.get_or_404(
                ExaminationSlot,
                int(request.form["slot_id"])
            )

            if slot.examiner_id != examiner.id:
                flash("You cannot delete another examiner's slot.")

            elif booking_has_started(slot.examination):
                flash("Slots cannot be deleted after booking begins.")

            elif slot.bookings:
                flash("Slots with existing bookings cannot be deleted.")

            else:
                db.session.delete(slot)
                db.session.commit()

                flash("Examination slot deleted successfully.")

        return redirect(url_for("manage_examiner_slots"))

    assignments = ExaminerAssignment.query.filter_by(
        examiner_id=examiner.id
    ).all()

    slots = ExaminationSlot.query.filter_by(
        examiner_id=examiner.id
    ).all()

    edit_id = request.args.get("edit_id", type=int)

    edit_slot = None

    if edit_id:
        edit_slot = db.session.get(ExaminationSlot, edit_id)

        if edit_slot and edit_slot.examiner_id != examiner.id:
            edit_slot = None
            flash("You cannot edit another examiner's slot.")

    return render_template(
        "examiner_slots.html",
        examiner=examiner,
        assignments=assignments,
        slots=slots,
        edit_slot=edit_slot
    )


if __name__ == "__main__":
    with app.app_context():
        from models import *
        db.create_all()
        print("Database tables created successfully.")
        print("All models and relationships loaded successfully.")


    app.run(debug=True)