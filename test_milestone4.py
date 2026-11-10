
import tempfile
from pathlib import Path
from datetime import date, datetime, time, timedelta

from flask import Flask
from werkzeug.security import generate_password_hash

from app import app as original_app
from extensions import db
from models import (
    User, Student, Examiner, Course, Examination,
    ExaminationSlot, Booking, ExaminerAssignment
)


# ============================================================
# SETUP: CREATE A SEPARATE TEST DATABASE AND REGISTER ROUTES
# ============================================================

temp_dir = tempfile.TemporaryDirectory()
database_path = Path(temp_dir.name) / "milestone4_test.db"

test_app = Flask(
    original_app.import_name,
    template_folder=original_app.template_folder,
    static_folder=None
)

test_app.config.update(
    SECRET_KEY="milestone4-test-secret",
    TESTING=True,
    SQLALCHEMY_DATABASE_URI=f"sqlite:///{database_path.as_posix()}",
    SQLALCHEMY_TRACK_MODIFICATIONS=False
)

db.init_app(test_app)

# Register the actual routes from app.py
for rule in original_app.url_map.iter_rules():

    if rule.endpoint == "static":
        continue

    test_app.add_url_rule(
        rule.rule,
        endpoint=rule.endpoint,
        view_func=original_app.view_functions[rule.endpoint],
        methods=rule.methods,
        defaults=rule.defaults,
        strict_slashes=rule.strict_slashes
    )

client = test_app.test_client()

results = []
ids = {}


def record(number, description, passed, detail=""):
    results.append((number, description, bool(passed)))

    status = "PASS" if passed else "FAIL"

    print(f"[{status}] Test {number:02d}: {description}")

    if detail:
        print("       ", detail)


def login_as(role, user_id):
    with client.session_transaction() as session:
        session.clear()
        session["user_id"] = user_id
        session["role"] = role


def post_as(role, user_id, url, data):
    login_as(role, user_id)
    return client.post(url, data=data, follow_redirects=True)


def get_as(role, user_id, url):
    login_as(role, user_id)
    return client.get(url, follow_redirects=False)


def contains(response, message):
    return message.lower() in response.get_data(as_text=True).lower()


def slot_form(exam_id, slot_date, start, end, capacity,
              action="add", slot_id=None):

    data = {
        "action": action,
        "exam_id": str(exam_id),
        "date": slot_date.strftime("%Y-%m-%d"),
        "start_time": start,
        "end_time": end,
        "capacity": str(capacity)
    }

    if slot_id is not None:
        data["slot_id"] = str(slot_id)

    return data


try:

    # ========================================================
    # CREATE TEST DATA
    # ========================================================

    with test_app.app_context():

        db.create_all()

        admin = User(
            full_name="Test Admin",
            email="admin_m4@test.local",
            password=generate_password_hash("test123"),
            role="admin"
        )

        approved_user = User(
            full_name="Approved Examiner",
            email="approved_m4@test.local",
            password=generate_password_hash("test123"),
            role="examiner"
        )

        pending_user = User(
            full_name="Pending Examiner",
            email="pending_m4@test.local",
            password=generate_password_hash("test123"),
            role="examiner"
        )

        other_user = User(
            full_name="Other Examiner",
            email="other_m4@test.local",
            password=generate_password_hash("test123"),
            role="examiner"
        )

        student_user = User(
            full_name="Test Student",
            email="student_m4@test.local",
            password=generate_password_hash("test123"),
            role="student"
        )

        db.session.add_all([
            admin, approved_user, pending_user,
            other_user, student_user
        ])

        db.session.flush()

        approved_examiner = Examiner(
            user_id=approved_user.id,
            department="Computer Science",
            contact="9000000001",
            status="approved"
        )

        pending_examiner = Examiner(
            user_id=pending_user.id,
            department="Computer Science",
            contact="9000000002",
            status="pending"
        )

        other_examiner = Examiner(
            user_id=other_user.id,
            department="Computer Science",
            contact="9000000003",
            status="approved"
        )

        student = Student(
            user_id=student_user.id,
            roll_number="M4TEST001",
            department="Computer Science",
            contact="9000000004"
        )

        course = Course(
            name="Milestone 4 Course",
            code="M4TEST",
            description="Test course",
            status="active"
        )

        db.session.add_all([
            approved_examiner,
            pending_examiner,
            other_examiner,
            student,
            course
        ])

        db.session.flush()

        exam = Examination(
            course_id=course.id,
            name="Milestone 4 Test Examination",
            exam_type="Practical",
            duration=60,
            max_marks=100,
            slot_creation_start=datetime.now() - timedelta(hours=1),
            slot_creation_end=datetime.now() + timedelta(days=10),
            booking_start=datetime.now() + timedelta(days=15),
            booking_end=datetime.now() + timedelta(days=20),
            slot_creation_open=True,
            booking_open=False,
            status="Published"
        )

        second_exam = Examination(
            course_id=course.id,
            name="Second Test Examination",
            exam_type="Practical",
            duration=60,
            max_marks=100,
            slot_creation_start=datetime.now() - timedelta(hours=1),
            slot_creation_end=datetime.now() + timedelta(days=10),
            booking_start=datetime.now() + timedelta(days=15),
            booking_end=datetime.now() + timedelta(days=20),
            slot_creation_open=True,
            booking_open=False,
            status="Published"
        )

        db.session.add_all([exam, second_exam])
        db.session.commit()

        ids.update({
            "admin": admin.id,
            "approved_user": approved_user.id,
            "pending_user": pending_user.id,
            "other_user": other_user.id,
            "student_user": student_user.id,
            "approved_examiner": approved_examiner.id,
            "pending_examiner": pending_examiner.id,
            "other_examiner": other_examiner.id,
            "student": student.id,
            "exam": exam.id,
            "second_exam": second_exam.id
        })

    tomorrow = date.today() + timedelta(days=1)

    # ========================================================
    # TESTS 1-5: ADMIN EXAMINER ASSIGNMENT
    # ========================================================

    post_as(
        "admin", ids["admin"], "/admin/management",
        {
            "action": "assign_examiner",
            "examiner_id": ids["approved_examiner"],
            "exam_id": ids["exam"]
        }
    )

    with test_app.app_context():

        assignment = ExaminerAssignment.query.filter_by(
            examiner_id=ids["approved_examiner"],
            exam_id=ids["exam"]
        ).first()

        assignment_id = assignment.id if assignment else None

    record(
        1,
        "Assign examination to approved examiner",
        assignment is not None
    )

    # Duplicate assignment
    post_as(
        "admin", ids["admin"], "/admin/management",
        {
            "action": "assign_examiner",
            "examiner_id": ids["approved_examiner"],
            "exam_id": ids["exam"]
        }
    )

    with test_app.app_context():

        count = ExaminerAssignment.query.filter_by(
            examiner_id=ids["approved_examiner"],
            exam_id=ids["exam"]
        ).count()

    record(2, "Prevent duplicate assignments", count == 1)

    # Pending examiner assignment
    post_as(
        "admin", ids["admin"], "/admin/management",
        {
            "action": "assign_examiner",
            "examiner_id": ids["pending_examiner"],
            "exam_id": ids["exam"]
        }
    )

    with test_app.app_context():

        pending_assignment = ExaminerAssignment.query.filter_by(
            examiner_id=ids["pending_examiner"],
            exam_id=ids["exam"]
        ).first()

    record(
        3,
        "Reject assignment to pending examiner",
        pending_assignment is None
    )

    # Remove assignment without slots
    post_as(
        "admin", ids["admin"], "/admin/management",
        {
            "action": "remove_assignment",
            "assignment_id": assignment_id
        }
    )

    with test_app.app_context():

        removed = db.session.get(
            ExaminerAssignment, assignment_id
        )

    record(4, "Remove assignment without slots", removed is None)

    # Reassign and create a slot
    post_as(
        "admin", ids["admin"], "/admin/management",
        {
            "action": "assign_examiner",
            "examiner_id": ids["approved_examiner"],
            "exam_id": ids["exam"]
        }
    )

    with test_app.app_context():

        assignment = ExaminerAssignment.query.filter_by(
            examiner_id=ids["approved_examiner"],
            exam_id=ids["exam"]
        ).first()

        ids["assignment"] = assignment.id

        existing_slot = ExaminationSlot(
            exam_id=ids["exam"],
            examiner_id=ids["approved_examiner"],
            date=tomorrow,
            start_time=time(8, 0),
            end_time=time(9, 0),
            capacity=2,
            available_seats=2,
            status="Available"
        )

        db.session.add(existing_slot)
        db.session.commit()

        ids["existing_slot"] = existing_slot.id

    post_as(
        "admin", ids["admin"], "/admin/management",
        {
            "action": "remove_assignment",
            "assignment_id": ids["assignment"]
        }
    )

    with test_app.app_context():

        assignment_exists = db.session.get(
            ExaminerAssignment, ids["assignment"]
        ) is not None

    record(
        5,
        "Prevent assignment removal while slots exist",
        assignment_exists
    )

    # ========================================================
    # TESTS 6-9: EXAMINER DASHBOARD AND ACCESS
    # ========================================================

    response = get_as(
        "examiner", ids["pending_user"],
        "/examiner/dashboard"
    )

    with client.session_transaction() as session:
        pending_logged_out = "user_id" not in session

    record(
        6,
        "Block unapproved examiner",
        response.status_code == 302 and pending_logged_out
    )

    response = get_as(
        "examiner", ids["approved_user"],
        "/examiner/dashboard"
    )

    dashboard = response.get_data(as_text=True)

    record(
        7,
        "Display assigned examinations",
        response.status_code == 200
        and "Milestone 4 Test Examination" in dashboard
    )

    record(
        8,
        "Display dashboard statistics",
        response.status_code == 200
        and "Assigned Exams" in dashboard
        and "Total Slots" in dashboard
        and "Available Slots" in dashboard
        and "Active Bookings" in dashboard
    )

    response = get_as(
        "student", ids["student_user"],
        "/examiner/dashboard"
    )

    record(
        9,
        "Prevent student access to examiner dashboard",
        response.status_code == 302
    )

    # ========================================================
    # TESTS 10-14: SLOT CREATION
    # ========================================================

    response = post_as(
        "examiner", ids["approved_user"],
        "/examiner/slots",
        slot_form(
            ids["exam"], tomorrow,
            "10:00", "11:00", 3
        )
    )

    with test_app.app_context():

        created_slot = ExaminationSlot.query.filter_by(
            examiner_id=ids["approved_examiner"],
            exam_id=ids["exam"],
            date=tomorrow,
            start_time=time(10, 0)
        ).first()

        ids["created_slot"] = (
            created_slot.id if created_slot else None
        )

    record(
        10,
        "Create slot within allowed timeline",
        created_slot is not None
    )

    # Close slot creation
    with test_app.app_context():

        exam = db.session.get(Examination, ids["exam"])
        exam.slot_creation_open = False
        db.session.commit()

        before = ExaminationSlot.query.filter_by(
            examiner_id=ids["approved_examiner"],
            exam_id=ids["exam"]
        ).count()

    post_as(
        "examiner", ids["approved_user"],
        "/examiner/slots",
        slot_form(
            ids["exam"], tomorrow + timedelta(days=1),
            "12:00", "13:00", 2
        )
    )

    with test_app.app_context():

        after = ExaminationSlot.query.filter_by(
            examiner_id=ids["approved_examiner"],
            exam_id=ids["exam"]
        ).count()

    record(11, "Reject slot creation when closed", before == after)

    # Outside timeline
    with test_app.app_context():

        exam = db.session.get(Examination, ids["exam"])
        exam.slot_creation_open = True
        exam.slot_creation_start = datetime.now() - timedelta(days=3)
        exam.slot_creation_end = datetime.now() - timedelta(days=2)
        db.session.commit()

        before = ExaminationSlot.query.filter_by(
            examiner_id=ids["approved_examiner"],
            exam_id=ids["exam"]
        ).count()

    post_as(
        "examiner", ids["approved_user"],
        "/examiner/slots",
        slot_form(
            ids["exam"], tomorrow + timedelta(days=2),
            "12:00", "13:00", 2
        )
    )

    with test_app.app_context():

        after = ExaminationSlot.query.filter_by(
            examiner_id=ids["approved_examiner"],
            exam_id=ids["exam"]
        ).count()

    record(12, "Reject slot creation outside timeline", before == after)

    # Restore allowed window
    with test_app.app_context():

        exam = db.session.get(Examination, ids["exam"])
        exam.slot_creation_open = True
        exam.slot_creation_start = datetime.now() - timedelta(hours=1)
        exam.slot_creation_end = datetime.now() + timedelta(days=10)
        db.session.commit()

        before = ExaminationSlot.query.filter_by(
            examiner_id=ids["approved_examiner"],
            exam_id=ids["exam"]
        ).count()

    # Invalid capacity
    invalid_capacity = post_as(
        "examiner", ids["approved_user"],
        "/examiner/slots",
        slot_form(
            ids["exam"], tomorrow + timedelta(days=3),
            "12:00", "13:00", 0
        )
    )

    # Invalid time range
    invalid_time = post_as(
        "examiner", ids["approved_user"],
        "/examiner/slots",
        slot_form(
            ids["exam"], tomorrow + timedelta(days=4),
            "13:00", "12:00", 2
        )
    )

    with test_app.app_context():

        after = ExaminationSlot.query.filter_by(
            examiner_id=ids["approved_examiner"],
            exam_id=ids["exam"]
        ).count()

    record(
        13,
        "Reject invalid capacity and time range",
        before == after
        and contains(
            invalid_capacity,
            "Capacity must be greater than zero."
        )
        and contains(
            invalid_time,
            "End time must be later than start time."
        )
    )

    # Overlapping slot
    post_as(
        "examiner", ids["approved_user"],
        "/examiner/slots",
        slot_form(
            ids["exam"], tomorrow,
            "10:30", "11:30", 2
        )
    )

    with test_app.app_context():

        overlap = ExaminationSlot.query.filter_by(
            examiner_id=ids["approved_examiner"],
            exam_id=ids["exam"],
            date=tomorrow,
            start_time=time(10, 30)
        ).first()

    record(14, "Reject overlapping slots", overlap is None)

    # ========================================================
    # TESTS 15-18: SLOT EDITING AND DELETION
    # ========================================================

    # Create a slot to edit
    with test_app.app_context():

        editable = ExaminationSlot(
            exam_id=ids["exam"],
            examiner_id=ids["approved_examiner"],
            date=tomorrow + timedelta(days=5),
            start_time=time(14, 0),
            end_time=time(15, 0),
            capacity=4,
            available_seats=4,
            status="Available"
        )

        db.session.add(editable)
        db.session.commit()

        editable_id = editable.id

    post_as(
        "examiner", ids["approved_user"],
        "/examiner/slots",
        slot_form(
            ids["exam"], tomorrow + timedelta(days=5),
            "15:00", "16:00", 5,
            action="edit",
            slot_id=editable_id
        )
    )

    with test_app.app_context():

        edited = db.session.get(
            ExaminationSlot, editable_id
        )

        edit_passed = (
            edited is not None
            and edited.start_time == time(15, 0)
            and edited.capacity == 5
        )

    record(15, "Edit slot before booking begins", edit_passed)

    # Delete a slot
    with test_app.app_context():

        deletable = ExaminationSlot(
            exam_id=ids["exam"],
            examiner_id=ids["approved_examiner"],
            date=tomorrow + timedelta(days=6),
            start_time=time(16, 0),
            end_time=time(17, 0),
            capacity=2,
            available_seats=2,
            status="Available"
        )

        db.session.add(deletable)
        db.session.commit()

        deletable_id = deletable.id

    post_as(
        "examiner", ids["approved_user"],
        "/examiner/slots",
        {
            "action": "delete",
            "slot_id": str(deletable_id)
        }
    )

    with test_app.app_context():

        deleted = db.session.get(
            ExaminationSlot, deletable_id
        )

    record(16, "Delete slot before booking begins", deleted is None)

    # Prevent editing/deleting after booking begins
    with test_app.app_context():

        exam = db.session.get(Examination, ids["exam"])
        exam.booking_start = datetime.now() - timedelta(minutes=1)

        locked = ExaminationSlot(
            exam_id=ids["exam"],
            examiner_id=ids["approved_examiner"],
            date=tomorrow + timedelta(days=7),
            start_time=time(17, 0),
            end_time=time(18, 0),
            capacity=2,
            available_seats=2,
            status="Available"
        )

        db.session.add(locked)
        db.session.commit()

        locked_id = locked.id

    edit_response = post_as(
        "examiner", ids["approved_user"],
        "/examiner/slots",
        slot_form(
            ids["exam"], tomorrow + timedelta(days=7),
            "18:00", "19:00", 3,
            action="edit",
            slot_id=locked_id
        )
    )

    delete_response = post_as(
        "examiner", ids["approved_user"],
        "/examiner/slots",
        {
            "action": "delete",
            "slot_id": str(locked_id)
        }
    )

    with test_app.app_context():

        locked_after = db.session.get(
            ExaminationSlot, locked_id
        )

        locked_unchanged = (
            locked_after is not None
            and locked_after.start_time == time(17, 0)
        )

        exam = db.session.get(Examination, ids["exam"])
        exam.booking_start = datetime.now() + timedelta(days=15)
        db.session.commit()

    record(
        17,
        "Prevent edit/delete after booking begins",
        locked_unchanged
        and contains(edit_response, "cannot be edited")
        and contains(delete_response, "cannot be deleted")
    )

    # Prevent edit/delete when bookings exist
    with test_app.app_context():

        booked_slot = ExaminationSlot(
            exam_id=ids["exam"],
            examiner_id=ids["approved_examiner"],
            date=tomorrow + timedelta(days=8),
            start_time=time(9, 0),
            end_time=time(10, 0),
            capacity=2,
            available_seats=1,
            status="Available"
        )

        db.session.add(booked_slot)
        db.session.flush()

        booking = Booking(
            student_id=ids["student"],
            slot_id=booked_slot.id,
            status="Booked"
        )

        db.session.add(booking)
        db.session.commit()

        booked_slot_id = booked_slot.id

    edit_response = post_as(
        "examiner", ids["approved_user"],
        "/examiner/slots",
        slot_form(
            ids["exam"], tomorrow + timedelta(days=8),
            "10:00", "11:00", 3,
            action="edit",
            slot_id=booked_slot_id
        )
    )

    delete_response = post_as(
        "examiner", ids["approved_user"],
        "/examiner/slots",
        {
            "action": "delete",
            "slot_id": str(booked_slot_id)
        }
    )

    with test_app.app_context():

        booked_slot_after = db.session.get(
            ExaminationSlot, booked_slot_id
        )

        booking_count = Booking.query.filter_by(
            slot_id=booked_slot_id
        ).count()

    record(
        18,
        "Prevent edit/delete when bookings exist",
        booked_slot_after is not None
        and booking_count == 1
        and contains(edit_response, "existing bookings")
        and contains(delete_response, "existing bookings")
    )

    # ========================================================
    # TESTS 19-20: BOOKED STUDENTS AND OWNERSHIP
    # ========================================================

    response = get_as(
        "examiner", ids["approved_user"],
        "/examiner/slots"
    )

    page = response.get_data(as_text=True)

    record(
        19,
        "Display booked student name and roll number",
        response.status_code == 200
        and "Test Student" in page
        and "M4TEST001" in page
    )

    # Create another examiner's slot
    with test_app.app_context():

        other_slot = ExaminationSlot(
            exam_id=ids["second_exam"],
            examiner_id=ids["other_examiner"],
            date=tomorrow + timedelta(days=9),
            start_time=time(11, 0),
            end_time=time(12, 0),
            capacity=2,
            available_seats=2,
            status="Available"
        )

        db.session.add(other_slot)
        db.session.commit()

        other_slot_id = other_slot.id

    # Try editing another examiner's slot
    edit_response = post_as(
        "examiner", ids["approved_user"],
        "/examiner/slots",
        slot_form(
            ids["second_exam"], tomorrow + timedelta(days=9),
            "12:00", "13:00", 3,
            action="edit",
            slot_id=other_slot_id
        )
    )

    # Try deleting another examiner's slot
    delete_response = post_as(
        "examiner", ids["approved_user"],
        "/examiner/slots",
        {
            "action": "delete",
            "slot_id": str(other_slot_id)
        }
    )

    with test_app.app_context():

        other_after = db.session.get(
            ExaminationSlot, other_slot_id
        )

        ownership_preserved = (
            other_after is not None
            and other_after.examiner_id == ids["other_examiner"]
            and other_after.start_time == time(11, 0)
        )

    record(
        20,
        "Prevent access to another examiner's slots",
        ownership_preserved
        and contains(edit_response, "another examiner")
        and contains(delete_response, "another examiner")
    )


finally:

    # Close temporary database connections
    try:
        with test_app.app_context():
            db.session.remove()
            db.engine.dispose()
    except Exception:
        pass

    temp_dir.cleanup()


# ============================================================
# FINAL TEST REPORT
# ============================================================

passed = sum(1 for _, _, result in results if result)
failed = len(results) - passed

print("\n" + "=" * 55)
print("       MILESTONE 4 AUTOMATED TEST RESULTS")
print("=" * 55)

print(f"Total Tests : {len(results)}")
print(f"Passed      : {passed}")
print(f"Failed      : {failed}")

if failed:

    print("\nFAILED TESTS:")

    for number, description, result in results:
        if not result:
            print(f"{number}. {description}")

    raise SystemExit(1)

else:

    print("\nALL 20 TESTS PASSED!")
    print("Milestone 4 functionality passed the automated tests.")
