
import os
import tempfile
from pathlib import Path
from datetime import datetime, timedelta, date, time

from app import app
from extensions import db
from models import (
    User,
    Student,
    Examiner,
    Course,
    Examination,
    ExaminationSlot,
    Booking
)


# --------------------------------------------------
# TEST DATABASE CONFIGURATION
# --------------------------------------------------

temp_dir = tempfile.TemporaryDirectory()
database_path = Path(temp_dir.name) / "milestone5_test.db"

app.config["SQLALCHEMY_DATABASE_URI"] = (
    "sqlite:///" + database_path.as_posix()
)

app.config["TESTING"] = True

client = app.test_client()


# --------------------------------------------------
# TEST COUNTERS
# --------------------------------------------------

passed = 0
failed = 0


# --------------------------------------------------
# DATABASE RESET FUNCTION
# --------------------------------------------------

def reset_database():

    db.session.remove()
    db.drop_all()
    db.create_all()


# --------------------------------------------------
# CREATE TEST DATA
# --------------------------------------------------

def create_test_data():

    # Student user
    student_user = User(
        full_name="Test Student",
        email="student@test.com",
        password="test123",
        role="student"
    )

    db.session.add(student_user)
    db.session.flush()

    student = Student(
        user_id=student_user.id,
        roll_number="TEST001",
        department="CSE",
        contact="9876543210"
    )

    # Second student
    second_user = User(
        full_name="Second Student",
        email="student2@test.com",
        password="test123",
        role="student"
    )

    db.session.add(second_user)
    db.session.flush()

    second_student = Student(
        user_id=second_user.id,
        roll_number="TEST002",
        department="CSE",
        contact="9876543211"
    )

    # Examiner user
    examiner_user = User(
        full_name="Test Examiner",
        email="examiner@test.com",
        password="test123",
        role="examiner"
    )

    db.session.add(examiner_user)
    db.session.flush()

    examiner = Examiner(
        user_id=examiner_user.id,
        department="CSE",
        contact="9876543212",
        status="approved"
    )

    # Course
    course = Course(
        name="Python Programming",
        code="PY101",
        description="Python course"
    )

    db.session.add_all([
        student,
        second_student,
        examiner,
        course
    ])

    db.session.flush()

    # Examination
    now = datetime.now()

    exam = Examination(
        course_id=course.id,
        name="Python Practical",
        exam_type="Practical",
        duration=60,
        max_marks=100,
        booking_start=now - timedelta(days=1),
        booking_end=now + timedelta(days=5),
        booking_open=True,
        status="Published"
    )

    db.session.add(exam)
    db.session.flush()

    # Second future examination slot
    slot_date = date.today() + timedelta(days=2)

    slot1 = ExaminationSlot(
        exam_id=exam.id,
        examiner_id=examiner.id,
        date=slot_date,
        start_time=time(9, 0),
        end_time=time(10, 0),
        capacity=2,
        available_seats=2,
        status="Available"
    )

    slot2 = ExaminationSlot(
        exam_id=exam.id,
        examiner_id=examiner.id,
        date=slot_date,
        start_time=time(10, 0),
        end_time=time(11, 0),
        capacity=2,
        available_seats=2,
        status="Available"
    )

    db.session.add_all([slot1, slot2])
    db.session.commit()

    return {
        "student": student,
        "second_student": second_student,
        "examiner": examiner,
        "course": course,
        "exam": exam,
        "slot1": slot1,
        "slot2": slot2
    }


# --------------------------------------------------
# STUDENT LOGIN SESSION
# --------------------------------------------------

def login_student(student):

    with client.session_transaction() as session:
        session["user_id"] = student.user_id
        session["role"] = "student"


# --------------------------------------------------
# TEST EXECUTION FUNCTION
# --------------------------------------------------

def run_test(test_number, description, test_function):

    global passed, failed

    try:
        reset_database()
        data = create_test_data()

        test_function(data)

        print(
            f"[PASS] Test {test_number}: {description}"
        )

        passed += 1

    except Exception as error:

        print(
            f"[FAIL] Test {test_number}: {description}"
        )

        print("       Error:", error)

        failed += 1

    finally:
        db.session.rollback()
        db.session.remove()


# --------------------------------------------------
# TEST 1: STUDENT DASHBOARD ACCESS
# --------------------------------------------------

def test_1(data):

    login_student(data["student"])

    response = client.get("/student/dashboard")

    assert response.status_code == 200


# --------------------------------------------------
# TEST 2: PREVENT UNAUTHENTICATED ACCESS
# --------------------------------------------------

def test_2(data):

    with client.session_transaction() as session:
        session.clear()

    response = client.get("/student/dashboard")

    assert response.status_code == 302
    assert "/login" in response.location


# --------------------------------------------------
# TEST 3: PREVENT NON-STUDENT ACCESS
# --------------------------------------------------

def test_3(data):

    with client.session_transaction() as session:
        session["user_id"] = 999
        session["role"] = "admin"

    response = client.get("/student/dashboard")

    assert response.status_code == 302


# --------------------------------------------------
# TEST 4: DISPLAY STUDENT NAME
# --------------------------------------------------

def test_4(data):

    login_student(data["student"])

    response = client.get("/student/dashboard")

    assert b"Test Student" in response.data


# --------------------------------------------------
# TEST 5: DISPLAY EXAMINATIONS
# --------------------------------------------------

def test_5(data):

    login_student(data["student"])

    response = client.get("/student/dashboard")

    assert b"Python Practical" in response.data


# --------------------------------------------------
# TEST 6: DYNAMIC EXAMINATION TYPE
# --------------------------------------------------

def test_6(data):

    exam = Examination(
        course_id=data["course"].id,
        name="Python Lab Assessment",
        exam_type="Lab Assessment",
        duration=90,
        max_marks=100
    )

    db.session.add(exam)
    db.session.commit()

    login_student(data["student"])

    response = client.get("/student/dashboard")

    assert b"Lab Assessment" in response.data


# --------------------------------------------------
# TEST 7: SEARCH EXAMINATION BY NAME
# --------------------------------------------------

def test_7(data):

    login_student(data["student"])

    response = client.get(
        "/student/dashboard?search=Python Practical"
    )

    assert response.status_code == 200
    assert b"Python Practical" in response.data


# --------------------------------------------------
# TEST 8: FILTER BY EXAMINATION TYPE
# --------------------------------------------------

def test_8(data):

    login_student(data["student"])

    response = client.get(
        "/student/dashboard?exam_type=Practical"
    )

    assert response.status_code == 200
    assert b"Python Practical" in response.data


# --------------------------------------------------
# TEST 9: FILTER BY COURSE
# --------------------------------------------------

def test_9(data):

    login_student(data["student"])

    course_id = data["course"].id

    response = client.get(
        f"/student/dashboard?course_id={course_id}"
    )

    assert response.status_code == 200
    assert b"Python Practical" in response.data


# --------------------------------------------------
# TEST 10: SUCCESSFUL SLOT BOOKING
# --------------------------------------------------

def test_10(data):

    login_student(data["student"])

    response = client.post(
        "/student/dashboard",
        data={
            "action": "book",
            "slot_id": data["slot1"].id
        }
    )

    booking = Booking.query.filter_by(
        student_id=data["student"].id,
        slot_id=data["slot1"].id,
        status="Booked"
    ).first()

    assert response.status_code == 302
    assert booking is not None
    assert data["slot1"].available_seats == 1


# --------------------------------------------------
# TEST 11: AUTOMATIC FULL SLOT STATUS
# --------------------------------------------------

def test_11(data):

    slot = data["slot1"]

    slot.capacity = 1
    slot.available_seats = 1

    db.session.commit()

    login_student(data["student"])

    client.post(
        "/student/dashboard",
        data={
            "action": "book",
            "slot_id": slot.id
        }
    )

    db.session.refresh(slot)

    assert slot.available_seats == 0
    assert slot.status == "Full"


# --------------------------------------------------
# TEST 12: PREVENT DUPLICATE EXAM BOOKING
# --------------------------------------------------

def test_12(data):

    login_student(data["student"])

    # First booking
    client.post(
        "/student/dashboard",
        data={
            "action": "book",
            "slot_id": data["slot1"].id
        }
    )

    # Try booking another slot for the same exam
    client.post(
        "/student/dashboard",
        data={
            "action": "book",
            "slot_id": data["slot2"].id
        }
    )

    bookings = Booking.query.filter_by(
        student_id=data["student"].id,
        status="Booked"
    ).all()

    assert len(bookings) == 1


# --------------------------------------------------
# TEST 13: REJECT BOOKING WHEN BOOKING IS CLOSED
# --------------------------------------------------

def test_13(data):

    exam = data["exam"]
    exam.booking_open = False

    db.session.commit()

    login_student(data["student"])

    client.post(
        "/student/dashboard",
        data={
            "action": "book",
            "slot_id": data["slot1"].id
        }
    )

    booking = Booking.query.filter_by(
        student_id=data["student"].id
    ).first()

    assert booking is None
    assert data["slot1"].available_seats == 2


# --------------------------------------------------
# TEST 14: REJECT BOOKING OUTSIDE TIMELINE
# --------------------------------------------------

def test_14(data):

    exam = data["exam"]

    exam.booking_start = datetime.now() - timedelta(days=5)
    exam.booking_end = datetime.now() - timedelta(days=1)
    exam.booking_open = True

    db.session.commit()

    login_student(data["student"])

    client.post(
        "/student/dashboard",
        data={
            "action": "book",
            "slot_id": data["slot1"].id
        }
    )

    booking = Booking.query.filter_by(
        student_id=data["student"].id
    ).first()

    assert booking is None


# --------------------------------------------------
# TEST 15: REJECT BOOKING FOR FULL SLOT
# --------------------------------------------------

def test_15(data):

    slot = data["slot1"]

    slot.available_seats = 0
    slot.status = "Full"

    db.session.commit()

    login_student(data["student"])

    client.post(
        "/student/dashboard",
        data={
            "action": "book",
            "slot_id": slot.id
        }
    )

    booking = Booking.query.filter_by(
        student_id=data["student"].id
    ).first()

    assert booking is None


# --------------------------------------------------
# TEST 16: REJECT BOOKING FOR PAST SLOT
# --------------------------------------------------

def test_16(data):

    slot = data["slot1"]

    slot.date = date.today() - timedelta(days=1)

    db.session.commit()

    login_student(data["student"])

    client.post(
        "/student/dashboard",
        data={
            "action": "book",
            "slot_id": slot.id
        }
    )

    booking = Booking.query.filter_by(
        student_id=data["student"].id
    ).first()

    assert booking is None


# --------------------------------------------------
# TEST 17: SUCCESSFUL BOOKING CANCELLATION
# --------------------------------------------------

def test_17(data):

    login_student(data["student"])

    # Book slot
    client.post(
        "/student/dashboard",
        data={
            "action": "book",
            "slot_id": data["slot1"].id
        }
    )

    booking = Booking.query.filter_by(
        student_id=data["student"].id
    ).first()

    assert booking is not None

    # Cancel booking
    client.post(
        "/student/dashboard",
        data={
            "action": "cancel",
            "booking_id": booking.id
        }
    )

    db.session.refresh(booking)
    db.session.refresh(data["slot1"])

    assert booking.status == "Cancelled"
    assert data["slot1"].available_seats == 2
    assert data["slot1"].status == "Available"


# --------------------------------------------------
# TEST 18: PREVENT CANCELLING ANOTHER STUDENT'S BOOKING
# --------------------------------------------------

def test_18(data):

    login_student(data["student"])

    # First student books a slot
    client.post(
        "/student/dashboard",
        data={
            "action": "book",
            "slot_id": data["slot1"].id
        }
    )

    booking = Booking.query.filter_by(
        student_id=data["student"].id
    ).first()

    # Log in as second student
    login_student(data["second_student"])

    client.post(
        "/student/dashboard",
        data={
            "action": "cancel",
            "booking_id": booking.id
        }
    )

    db.session.refresh(booking)

    assert booking.status == "Booked"


# --------------------------------------------------
# TEST 19: REJECT CANCELLATION AFTER DEADLINE
# --------------------------------------------------

def test_19(data):

    login_student(data["student"])

    # Create booking
    client.post(
        "/student/dashboard",
        data={
            "action": "book",
            "slot_id": data["slot1"].id
        }
    )

    booking = Booking.query.filter_by(
        student_id=data["student"].id
    ).first()

    # Move cancellation deadline into the past
    data["exam"].booking_end = datetime.now() - timedelta(days=1)

    db.session.commit()

    # Attempt cancellation
    client.post(
        "/student/dashboard",
        data={
            "action": "cancel",
            "booking_id": booking.id
        }
    )

    db.session.refresh(booking)

    assert booking.status == "Booked"


# --------------------------------------------------
# TEST 20: PRESERVE CANCELLED BOOKING HISTORY
# --------------------------------------------------

def test_20(data):

    login_student(data["student"])

    # Book slot
    client.post(
        "/student/dashboard",
        data={
            "action": "book",
            "slot_id": data["slot1"].id
        }
    )

    booking = Booking.query.filter_by(
        student_id=data["student"].id
    ).first()

    # Cancel booking
    client.post(
        "/student/dashboard",
        data={
            "action": "cancel",
            "booking_id": booking.id
        }
    )

    # Check dashboard history
    response = client.get("/student/dashboard")

    assert response.status_code == 200
    assert b"Cancelled" in response.data

    # Check database record still exists
    saved_booking = db.session.get(Booking, booking.id)

    assert saved_booking is not None
    assert saved_booking.status == "Cancelled"


# --------------------------------------------------
# RUN ALL 20 TESTS
# --------------------------------------------------

if __name__ == "__main__":

    print("\n======================================")
    print(" MILESTONE 5 AUTOMATED TESTING")
    print(" Student Dashboard and Slot Booking")
    print("======================================\n")

    try:

        with app.app_context():

            db.create_all()

            tests = [
                (1, "Student dashboard access", test_1),
                (2, "Prevent unauthenticated access", test_2),
                (3, "Prevent non-student access", test_3),
                (4, "Display student name", test_4),
                (5, "Display examinations", test_5),
                (6, "Dynamic examination types", test_6),
                (7, "Search examination by name", test_7),
                (8, "Filter by examination type", test_8),
                (9, "Filter by course", test_9),
                (10, "Successful slot booking", test_10),
                (11, "Automatic full slot status", test_11),
                (12, "Prevent duplicate exam booking", test_12),
                (13, "Reject booking when closed", test_13),
                (14, "Reject booking outside timeline", test_14),
                (15, "Reject booking for full slot", test_15),
                (16, "Reject booking for past slot", test_16),
                (17, "Successful booking cancellation", test_17),
                (18, "Prevent cancelling another student's booking", test_18),
                (19, "Reject cancellation after deadline", test_19),
                (20, "Preserve cancelled booking history", test_20)
            ]

            for number, description, function in tests:

                run_test(number, description, function)

            print("\n======================================")
            print(" MILESTONE 5 TEST RESULTS")
            print("======================================")

            print("Total Tests :", passed + failed)
            print("Passed      :", passed)
            print("Failed      :", failed)

            if failed == 0:
                print("\nALL 20 TESTS PASSED!")
                print("Milestone 5 automated tests successful.")
            else:
                print("\nSOME TESTS FAILED.")
                print("Fix the failed tests before committing.")

            print("======================================")

    finally:

        with app.app_context():
            db.session.remove()
            db.engine.dispose()

        temp_dir.cleanup()
