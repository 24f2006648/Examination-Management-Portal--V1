
"""
Milestone 6 Tests - Examination Booking History and Evaluation Tracking


"""

import tempfile
import uuid
from datetime import date, datetime, time, timedelta
from pathlib import Path

from flask import Flask
from werkzeug.security import generate_password_hash

from app import app as original_app
from extensions import db

from models import (
    User,
    Student,
    Examiner,
    Course,
    Examination,
    ExaminationRubric,
    ExaminationSlot,
    Booking,
    Evaluation,
    EvaluationDetail,
)


# ============================================================
# 1. TEMPORARY TEST APPLICATION
# ============================================================

temp_dir = tempfile.TemporaryDirectory()

database_path = Path(temp_dir.name) / "milestone6_test.db"

test_app = Flask(
    original_app.import_name,
    template_folder=original_app.template_folder,
    static_folder=None,
)

test_app.config.update(
    SECRET_KEY="milestone6-test-secret",
    TESTING=True,
    SQLALCHEMY_DATABASE_URI=f"sqlite:///{database_path.as_posix()}",
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
)

db.init_app(test_app)


# Register actual routes from app.py
for rule in original_app.url_map.iter_rules():

    if rule.endpoint == "static":
        continue

    test_app.add_url_rule(
        rule.rule,
        endpoint=rule.endpoint,
        view_func=original_app.view_functions[rule.endpoint],
        methods=rule.methods,
        defaults=rule.defaults,
        strict_slashes=rule.strict_slashes,
    )


client = test_app.test_client()

results = []

run_id = uuid.uuid4().hex[:8]


# ============================================================
# 2. HELPER FUNCTIONS
# ============================================================

def record(description, passed, detail=""):

    results.append((description, bool(passed)))

    status = "PASS" if passed else "FAIL"

    print(f"[{status}] {description}")

    if detail:
        print("       " + detail)


def login_as(role, user_id):

    with client.session_transaction() as session:

        session.clear()

        session["user_id"] = user_id
        session["role"] = role


def admin_post(data):

    login_as("admin", ids["admin_user"])

    return client.post(
        "/admin/management",
        data=data,
        follow_redirects=True,
    )


def examiner_get(path):

    login_as("examiner", ids["examiner_user"])

    return client.get(
        path,
        follow_redirects=False,
    )


def examiner_post(path, data):

    login_as("examiner", ids["examiner_user"])

    return client.post(
        path,
        data=data,
        follow_redirects=True,
    )


def make_marks(
    first,
    second,
    remarks="Milestone 6 test feedback",
):

    return {
        f"mark_{ids['rubric1']}": str(first),
        f"mark_{ids['rubric2']}": str(second),
        f"mark_{ids['rubric3']}": "0",
        "remarks": remarks,
    }


# ============================================================
# 3. CREATE TEST DATABASE AND SAMPLE DATA
# ============================================================

try:

    with test_app.app_context():

        db.create_all()

        # ----------------------------------------------------
        # Create users
        # ----------------------------------------------------

        admin_user = User(
            full_name="Milestone 6 Admin",
            email=f"admin_{run_id}@test.local",
            password=generate_password_hash("admin123"),
            role="admin",
        )

        student_user = User(
            full_name="Milestone 6 Student",
            email=f"student_{run_id}@test.local",
            password=generate_password_hash("student123"),
            role="student",
        )

        examiner_user = User(
            full_name="Assigned Examiner",
            email=f"examiner_{run_id}@test.local",
            password=generate_password_hash("examiner123"),
            role="examiner",
        )

        other_examiner_user = User(
            full_name="Other Examiner",
            email=f"other_{run_id}@test.local",
            password=generate_password_hash("examiner123"),
            role="examiner",
        )

        db.session.add_all([
            admin_user,
            student_user,
            examiner_user,
            other_examiner_user,
        ])

        db.session.flush()

        # ----------------------------------------------------
        # Create student and examiners
        # ----------------------------------------------------

        student = Student(
            user_id=student_user.id,
            roll_number=f"M6{run_id}",
            department="CSE",
            contact="9000000001",
        )

        examiner = Examiner(
            user_id=examiner_user.id,
            department="CSE",
            contact="9000000002",
            status="approved",
        )

        other_examiner = Examiner(
            user_id=other_examiner_user.id,
            department="CSE",
            contact="9000000003",
            status="approved",
        )

        course = Course(
            name="Milestone 6 Course",
            code=f"M6{run_id}",
            description="Evaluation testing course",
            status="active",
        )

        db.session.add_all([
            student,
            examiner,
            other_examiner,
            course,
        ])

        db.session.flush()

        # ----------------------------------------------------
        # Create examination
        # ----------------------------------------------------

        exam = Examination(
            course_id=course.id,
            name="Milestone 6 Practical Examination",
            exam_type="Practical",
            duration=60,
            max_marks=100,
            booking_start=datetime.now() - timedelta(days=1),
            booking_end=datetime.now() + timedelta(days=5),
            booking_open=True,
            status="Published",
        )

        db.session.add(exam)

        db.session.flush()

        # ----------------------------------------------------
        # Create three rubrics
        # ----------------------------------------------------

        rubric1 = ExaminationRubric(
            exam_id=exam.id,
            criterion_name="Technical Knowledge",
            max_marks=60,
            weightage=60,
            description="Technical skills",
        )

        rubric2 = ExaminationRubric(
            exam_id=exam.id,
            criterion_name="Practical Skills",
            max_marks=60,
            weightage=40,
            description="Practical implementation",
        )

        rubric3 = ExaminationRubric(
            exam_id=exam.id,
            criterion_name="Communication Skills",
            max_marks=10,
            weightage=10,
            description="Communication skills",
        )

        db.session.add_all([
            rubric1,
            rubric2,
            rubric3,
        ])

        db.session.flush()

        # ----------------------------------------------------
        # Create examination slots
        # ----------------------------------------------------

        slot = ExaminationSlot(
            exam_id=exam.id,
            examiner_id=examiner.id,
            date=date.today() + timedelta(days=1),
            start_time=time(9, 0),
            end_time=time(10, 0),
            capacity=20,
            available_seats=19,
            status="Available",
        )

        other_slot = ExaminationSlot(
            exam_id=exam.id,
            examiner_id=other_examiner.id,
            date=date.today() + timedelta(days=1),
            start_time=time(10, 0),
            end_time=time(11, 0),
            capacity=20,
            available_seats=19,
            status="Available",
        )

        db.session.add_all([
            slot,
            other_slot,
        ])

        db.session.flush()

        # ----------------------------------------------------
        # Create bookings
        # ----------------------------------------------------

        booking = Booking(
            student_id=student.id,
            slot_id=slot.id,
            status="Booked",
        )

        other_booking = Booking(
            student_id=student.id,
            slot_id=other_slot.id,
            status="Booked",
        )

        db.session.add_all([
            booking,
            other_booking,
        ])

        db.session.commit()

        # ----------------------------------------------------
        # Store database IDs
        # ----------------------------------------------------

        ids = {
            "admin_user": admin_user.id,
            "student_user": student_user.id,
            "examiner_user": examiner_user.id,
            "other_examiner_user": other_examiner_user.id,

            "student": student.id,
            "examiner": examiner.id,
            "other_examiner": other_examiner.id,

            "exam": exam.id,

            "rubric1": rubric1.id,
            "rubric2": rubric2.id,
            "rubric3": rubric3.id,

            "slot": slot.id,
            "other_slot": other_slot.id,

            "booking": booking.id,
            "other_booking": other_booking.id,
        }


    # ========================================================
    # 4. ACCESS CONTROL TESTS
    # ========================================================

    response = client.get(
        f"/examiner/evaluate/{ids['booking']}"
    )

    record(
        "Unauthenticated user cannot open evaluation page",
        response.status_code == 302,
    )


    login_as("student", ids["student_user"])

    response = client.get(
        f"/examiner/evaluate/{ids['booking']}"
    )

    record(
        "Student cannot access examiner evaluation route",
        response.status_code == 302,
    )


    login_as("examiner", ids["other_examiner_user"])

    response = client.get(
        f"/examiner/evaluate/{ids['booking']}"
    )

    record(
        "Examiner cannot evaluate another examiner's booking",
        response.status_code == 302,
    )


    # ========================================================
    # 5. EVALUATION PAGE TEST
    # ========================================================

    response = examiner_get(
        f"/examiner/evaluate/{ids['booking']}"
    )

    record(
        "Assigned examiner can open evaluation page",
        response.status_code == 200
        and b"Technical Knowledge" in response.data,
        "Requires examiner_evaluations.html template.",
    )


    # ========================================================
    # 6. VALID EVALUATION SUBMISSION
    # ========================================================

    examiner_post(
        f"/examiner/evaluate/{ids['booking']}",
        make_marks(30, 40),
    )

    with test_app.app_context():

        evaluation = Evaluation.query.filter_by(
            booking_id=ids["booking"]
        ).first()

        saved_details = []

        if evaluation:

            saved_details = EvaluationDetail.query.filter_by(
                evaluation_id=evaluation.id
            ).all()

        saved_booking = db.session.get(
            Booking,
            ids["booking"],
        )

        valid_saved = (
            evaluation is not None
            and evaluation.marks == 70
            and evaluation.status == "Published"
            and len(saved_details) == 3
            and saved_booking.status == "Completed"
        )

    record(
        "Valid evaluation publishes total and criterion-wise marks",
        valid_saved,
    )


    # ========================================================
    # 7. INVALID MARKS VALIDATION TESTS
    # ========================================================

    invalid_cases = [

        (
            "Reject missing criterion marks",
            {
                f"mark_{ids['rubric1']}": "20",
                f"mark_{ids['rubric2']}": "20",
                "remarks": "Missing third criterion",
            },
        ),

        (
            "Reject negative marks",
            make_marks(-1, 20),
        ),

        (
            "Reject marks above rubric maximum",
            make_marks(61, 20),
        ),

        (
            "Reject total above examination maximum",
            make_marks(60, 50),
        ),

        (
            "Reject NaN marks",
            make_marks("nan", 20),
        ),

        (
            "Reject infinite marks",
            make_marks("inf", 20),
        ),

        (
            "Reject non-numeric marks",
            make_marks("abc", 20),
        ),
    ]


    for description, data in invalid_cases:

        # Create a fresh booking for each invalid test.

        with test_app.app_context():

            fresh_booking = Booking(
                student_id=ids["student"],
                slot_id=ids["slot"],
                status="Booked",
            )

            db.session.add(fresh_booking)

            db.session.commit()

            fresh_booking_id = fresh_booking.id


        examiner_post(
            f"/examiner/evaluate/{fresh_booking_id}",
            data,
        )


        with test_app.app_context():

            no_evaluation = (
                Evaluation.query.filter_by(
                    booking_id=fresh_booking_id
                ).first() is None
            )

            fresh_booking_record = db.session.get(
                Booking,
                fresh_booking_id,
            )

            still_booked = (
                fresh_booking_record is not None
                and fresh_booking_record.status == "Booked"
            )


        record(
            description,
            no_evaluation and still_booked,
        )


    # ========================================================
    # 8. UPDATE EXISTING EVALUATION
    # ========================================================

    examiner_post(
        f"/examiner/evaluate/{ids['booking']}",
        make_marks(
            35,
            45,
            "Updated feedback",
        ),
    )


    with test_app.app_context():

        updated_evaluation = Evaluation.query.filter_by(
            booking_id=ids["booking"]
        ).first()

        update_ok = False

        if updated_evaluation:

            updated_details = EvaluationDetail.query.filter_by(
                evaluation_id=updated_evaluation.id
            ).all()

            updated_detail_marks = sorted(
                detail.marks_awarded
                for detail in updated_details
            )

            update_ok = (
                updated_evaluation.marks == 80
                and updated_evaluation.remarks == "Updated feedback"
                and updated_detail_marks == [0.0, 35.0, 45.0]
                and len(updated_details) == 3
            )


    record(
        "Revised evaluation updates latest marks and feedback",
        update_ok,
    )


    # ========================================================
    # 9. RUBRIC DELETION PROTECTION
    # ========================================================

    # First, try deleting a rubric used in the evaluation.

    admin_post({
        "action": "delete_rubric",
        "rubric_id": ids["rubric1"],
    })


    with test_app.app_context():

        used_rubric_remains = (
            db.session.get(
                ExaminationRubric,
                ids["rubric1"],
            ) is not None
        )


    record(
        "Admin cannot delete a rubric already used in evaluation",
        used_rubric_remains,
    )


    # Create a new rubric that has never been used.

    with test_app.app_context():

        unused_rubric = ExaminationRubric(
            exam_id=ids["exam"],
            criterion_name="Unused Criterion",
            max_marks=10,
            weightage=10,
            description="Not used in evaluation",
        )

        db.session.add(unused_rubric)

        db.session.commit()

        unused_rubric_id = unused_rubric.id


    # Try deleting the unused rubric.

    admin_post({
        "action": "delete_rubric",
        "rubric_id": unused_rubric_id,
    })


    with test_app.app_context():

        unused_rubric_deleted = (
            db.session.get(
                ExaminationRubric,
                unused_rubric_id,
            ) is None
        )


    record(
        "Admin can delete a rubric that has not been used",
        unused_rubric_deleted,
    )


    # ========================================================
    # 10. ADMIN EVALUATION HISTORY
    # ========================================================

    login_as("admin", ids["admin_user"])

    response = client.get("/admin/management")

    admin_history_visible = (
        response.status_code == 200
        and b"Milestone 6 Student" in response.data
        and b"Updated feedback" in response.data
    )

    record(
        "Admin can view evaluation history and feedback",
        admin_history_visible,
        "Requires evaluation history in admin_management.html.",
    )


    # ========================================================
    # 11. STUDENT RESULTS AND FEEDBACK
    # ========================================================

    login_as("student", ids["student_user"])

    response = client.get("/student/dashboard")

    student_result_visible = (
        response.status_code == 200
        and b"80" in response.data
        and b"Updated feedback" in response.data
        and b"Completed" in response.data
    )

    record(
        "Student can view published results and feedback",
        student_result_visible,
        "Requires published results in student_dashboard.html.",
    )


    # ========================================================
    # 12. FINAL TEST SUMMARY
    # ========================================================

    print("\n========== MILESTONE 6 TEST SUMMARY ==========")

    passed = sum(
        1 for _, status in results if status
    )

    failed = len(results) - passed

    print(f"Total tests : {len(results)}")
    print(f"Passed      : {passed}")
    print(f"Failed      : {failed}")


    if failed:

        print("\nFailed tests:")

        for description, status in results:

            if not status:
                print(" -", description)


finally:

    with test_app.app_context():

        db.session.remove()

        db.engine.dispose()

    temp_dir.cleanup()
