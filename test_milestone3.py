
import os
import tempfile
import uuid
from datetime import date, time
from flask import Flask
from werkzeug.security import generate_password_hash

from app import app as original_app
from extensions import db
from models import (
    User, Student, Examiner, Course, Examination,
    ExaminationRubric, ExaminationSlot, Booking
)

# ==================================================
# 1. CREATE TEMPORARY FLASK APP WITH REAL ROUTES
# ==================================================

temp_dir = tempfile.TemporaryDirectory()
db_path = os.path.join(temp_dir.name, "milestone3_test.db")

test_app = Flask(
    original_app.import_name,
    template_folder=original_app.template_folder,
    static_folder=None
)

test_app.config.update(
    SECRET_KEY="temporary-test-secret",
    TESTING=True,
    SQLALCHEMY_DATABASE_URI="sqlite:///" + db_path.replace("\\", "/"),
    SQLALCHEMY_TRACK_MODIFICATIONS=False
)

# Register SQLAlchemy with the temporary application.
db.init_app(test_app)

# Copy the actual routes and their existing view functions.
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

# Unique values for every execution.
RUN_ID = uuid.uuid4().hex[:10]

ADMIN_EMAIL = f"admin_{RUN_ID}@test.com"
STUDENT_EMAIL = f"student_{RUN_ID}@test.com"
EXAMINER_EMAIL = f"examiner_{RUN_ID}@test.com"
EXAMINER2_EMAIL = f"examiner2_{RUN_ID}@test.com"
ROLL_NUMBER = f"R{RUN_ID}"
COURSE_CODE = f"C{RUN_ID}"

results = []


def check(name, condition):
    passed = bool(condition)
    results.append(passed)

    print(
        f"{'PASS' if passed else 'FAIL'}: {name}"
    )


def admin_post(client, data):
    return client.post(
        "/admin/management",
        data=data,
        follow_redirects=True
    )


try:
    with test_app.app_context():

        # ==================================================
        # 2. CREATE TEMPORARY DATABASE TABLES
        # ==================================================

        db.create_all()

        # ==================================================
        # 3. CREATE TEST USERS
        # ==================================================

        admin = User(
            full_name="Test Admin",
            email=ADMIN_EMAIL,
            password=generate_password_hash("admin123"),
            role="admin"
        )

        student_user = User(
            full_name="Test Student",
            email=STUDENT_EMAIL,
            password=generate_password_hash("student123"),
            role="student"
        )

        examiner_user = User(
            full_name="Test Examiner",
            email=EXAMINER_EMAIL,
            password=generate_password_hash("examiner123"),
            role="examiner"
        )

        examiner2_user = User(
            full_name="Second Examiner",
            email=EXAMINER2_EMAIL,
            password=generate_password_hash("examiner123"),
            role="examiner"
        )

        db.session.add_all([
            admin,
            student_user,
            examiner_user,
            examiner2_user
        ])

        db.session.flush()

        student = Student(
            user_id=student_user.id,
            roll_number=ROLL_NUMBER,
            department="CSE",
            contact="9999999999"
        )

        examiner = Examiner(
            user_id=examiner_user.id,
            department="CSE",
            contact="8888888888",
            status="approved"
        )

        examiner2 = Examiner(
            user_id=examiner2_user.id,
            department="CSE",
            contact="7777777777",
            status="approved"
        )

        db.session.add_all([
            student,
            examiner,
            examiner2
        ])

        db.session.commit()

        client = test_app.test_client()

        with client.session_transaction() as session:
            session["user_id"] = admin.id
            session["role"] = "admin"

        # ==================================================
        # TEST 1: COURSE ADD, VIEW, EDIT AND DELETE
        # ==================================================

        response = client.post(
            "/admin/courses",
            data={
                "action": "add",
                "name": "Temporary Course",
                "code": COURSE_CODE,
                "description": "Course testing"
            },
            follow_redirects=True
        )

        course = Course.query.filter_by(
            code=COURSE_CODE
        ).first()

        added = course is not None

        response = client.get("/admin/courses")

        viewed = (
            response.status_code == 200
            and COURSE_CODE.encode() in response.data
        )

        if course:
            course_id = course.id

            client.post(
                "/admin/courses",
                data={
                    "action": "edit",
                    "course_id": course_id,
                    "name": "Updated Course",
                    "code": COURSE_CODE,
                    "description": "Updated description"
                },
                follow_redirects=True
            )

            db.session.refresh(course)
            edited = course.name == "Updated Course"

            client.post(
                "/admin/courses",
                data={
                    "action": "delete",
                    "course_id": course_id
                },
                follow_redirects=True
            )

            deleted = db.session.get(Course, course_id) is None
        else:
            edited = False
            deleted = False

        check(
            "1. Course Add/View/Edit/Delete",
            added and viewed and edited and deleted
        )

        # Create a course for examination testing.
        course = Course(
            name="Testing Statistics",
            code=COURSE_CODE,
            description="Examination test course"
        )

        db.session.add(course)
        db.session.commit()

        # ==================================================
        # TEST 2: EXAMINATION ADD, VIEW AND EDIT
        # ==================================================

        client.post(
            "/admin/examinations",
            data={
                "action": "add",
                "course_id": course.id,
                "name": "Test CAT",
                "exam_type": "CAT",
                "duration": "60",
                "max_marks": "100"
            },
            follow_redirects=True
        )

        exam = Examination.query.filter_by(
            name="Test CAT"
        ).first()

        added = exam is not None

        response = client.get("/admin/examinations")

        viewed = (
            response.status_code == 200
            and b"Test CAT" in response.data
        )

        if exam:
            exam_id = exam.id

            client.post(
                "/admin/examinations",
                data={
                    "action": "edit",
                    "exam_id": exam_id,
                    "course_id": course.id,
                    "name": "Updated CAT",
                    "exam_type": "CAT",
                    "duration": "90",
                    "max_marks": "100"
                },
                follow_redirects=True
            )

            db.session.refresh(exam)

            edited = (
                exam.name == "Updated CAT"
                and exam.duration == 90
            )
        else:
            edited = False

        check(
            "2. Examination Add/View/Edit",
            added and viewed and edited
        )

        if not exam:
            raise RuntimeError(
                "Examination creation failed. "
                "Further tests cannot continue."
            )

        # ==================================================
        # TEST 3: RUBRIC ADD AND DELETE
        # ==================================================

        admin_post(client, {
            "action": "add_rubric",
            "exam_id": exam.id,
            "criterion_name": "Technical Knowledge",
            "max_marks": "50",
            "weightage": "50",
            "description": "Technical evaluation"
        })

        rubric = ExaminationRubric.query.filter_by(
            exam_id=exam.id
        ).first()

        rubric_added = rubric is not None

        if rubric:
            rubric_id = rubric.id

            admin_post(client, {
                "action": "delete_rubric",
                "rubric_id": rubric_id
            })

            rubric_deleted = (
                db.session.get(
                    ExaminationRubric, rubric_id
                ) is None
            )
        else:
            rubric_deleted = False

        check(
            "3. Rubric Add/Delete",
            rubric_added and rubric_deleted
        )

        # ==================================================
        # TEST 4: EXAMINER ACTIVATION AND DEACTIVATION
        # ==================================================

        admin_post(client, {
            "action": "deactivate_examiner",
            "examiner_id": examiner.id
        })

        db.session.refresh(examiner)
        deactivated = examiner.status == "inactive"

        admin_post(client, {
            "action": "activate_examiner",
            "examiner_id": examiner.id
        })

        db.session.refresh(examiner)
        activated = examiner.status == "approved"

        check(
            "4. Examiner Activation/Deactivation",
            deactivated and activated
        )

        # ==================================================
        # TEST 5: EXAMINATION TIMELINES
        # ==================================================

        admin_post(client, {
            "action": "update_timeline",
            "exam_id": exam.id,
            "slot_creation_start": "2026-11-11T09:00",
            "slot_creation_end": "2026-11-12T17:00",
            "booking_start": "2026-11-13T09:00",
            "booking_end": "2026-11-14T17:00"
        })

        db.session.refresh(exam)

        timeline_updated = all([
            exam.slot_creation_start,
            exam.slot_creation_end,
            exam.booking_start,
            exam.booking_end
        ])

        check("5. Examination Timelines", timeline_updated)

        # ==================================================
        # TEST 6: SLOT CREATION OPEN/CLOSE
        # ==================================================

        admin_post(client, {
            "action": "toggle_slots",
            "exam_id": exam.id
        })

        db.session.refresh(exam)
        opened = exam.slot_creation_open is True

        admin_post(client, {
            "action": "toggle_slots",
            "exam_id": exam.id
        })

        db.session.refresh(exam)
        closed = exam.slot_creation_open is False

        check("6. Slot Creation Open/Close", opened and closed)

        # ==================================================
        # TEST 7: BOOKING OPEN/CLOSE
        # ==================================================

        admin_post(client, {
            "action": "toggle_booking",
            "exam_id": exam.id
        })

        db.session.refresh(exam)
        opened = exam.booking_open is True

        admin_post(client, {
            "action": "toggle_booking",
            "exam_id": exam.id
        })

        db.session.refresh(exam)
        closed = exam.booking_open is False

        check("7. Booking Open/Close", opened and closed)

        # ==================================================
        # CREATE TEST SLOTS
        # ==================================================

        old_slot = ExaminationSlot(
            exam_id=exam.id,
            examiner_id=examiner.id,
            date=date(2026, 11, 20),
            start_time=time(9, 0),
            end_time=time(10, 0),
            capacity=1,
            available_seats=0,
            status="Full"
        )

        new_slot = ExaminationSlot(
            exam_id=exam.id,
            examiner_id=examiner2.id,
            date=date(2026, 11, 21),
            start_time=time(10, 0),
            end_time=time(11, 0),
            capacity=2,
            available_seats=2,
            status="Available"
        )

        db.session.add_all([old_slot, new_slot])
        db.session.commit()

        # ==================================================
        # TEST 8: VIEW EXAMINATION SLOTS
        # ==================================================

        response = client.get("/admin/management")

        slots_viewed = (
            response.status_code == 200
            and str(old_slot.id).encode() in response.data
        )

        check("8. View Examination Slots", slots_viewed)

        # ==================================================
        # TEST 9: CHANGE ASSIGNED EXAMINER
        # ==================================================

        admin_post(client, {
            "action": "change_examiner",
            "slot_id": old_slot.id,
            "examiner_id": examiner2.id
        })

        db.session.refresh(old_slot)

        examiner_changed = (
            old_slot.examiner_id == examiner2.id
        )

        check("9. Change Assigned Examiner", examiner_changed)

        # Restore original examiner for booking test.
        old_slot.examiner_id = examiner.id

        # ==================================================
        # CREATE TEST BOOKINGS
        # ==================================================

        booking = Booking(
            student_id=student.id,
            slot_id=old_slot.id,
            status="Booked"
        )

        historical_booking = Booking(
            student_id=student.id,
            slot_id=new_slot.id,
            status="Cancelled"
        )

        db.session.add_all([booking, historical_booking])
        db.session.commit()

        # ==================================================
        # TEST 10: VIEW BOOKING RECORDS
        # ==================================================

        response = client.get("/admin/management")

        bookings_viewed = (
            response.status_code == 200
            and str(booking.id).encode() in response.data
        )

        check("10. View Booking Records", bookings_viewed)

        # ==================================================
        # TEST 11: RESCHEDULE BOOKING
        # ==================================================

        admin_post(client, {
            "action": "reschedule_booking",
            "booking_id": booking.id,
            "new_slot_id": new_slot.id
        })

        db.session.refresh(booking)
        db.session.refresh(old_slot)
        db.session.refresh(new_slot)

        rescheduled = (
            booking.slot_id == new_slot.id
            and old_slot.available_seats == old_slot.capacity
            and new_slot.available_seats == 1
        )

        check("11. Booking Rescheduling", rescheduled)

        # ==================================================
        # TEST 12: ADMIN DASHBOARD STATISTICS
        # ==================================================

        response = client.get("/admin/dashboard")

        dashboard_works = (
            response.status_code == 200
            and b"Admin Dashboard Overview" in response.data
        )

        check("12. Admin Dashboard Statistics", dashboard_works)

        # ==================================================
        # TEST 13: HISTORICAL BOOKING PRESERVATION
        # ==================================================

        historical = db.session.get(
            Booking, historical_booking.id
        )

        history_preserved = (
            historical is not None
            and historical.status == "Cancelled"
            and Booking.query.count() == 2
        )

        check(
            "13. Historical Booking Preservation",
            history_preserved
        )

        # ==================================================
        # ADDITIONAL TEST: EXAMINATION DELETE
        # ==================================================

        # Remove dependent test records first.
        db.session.delete(booking)
        db.session.delete(historical_booking)
        db.session.delete(old_slot)
        db.session.delete(new_slot)
        db.session.commit()

        client.post(
            "/admin/examinations",
            data={
                "action": "delete",
                "exam_id": exam.id
            },
            follow_redirects=True
        )

        exam_deleted = (
            db.session.get(Examination, exam.id) is None
        )

        check("Additional: Examination Delete", exam_deleted)

        # ==================================================
        # FINAL RESULTS
        # ==================================================

        passed = sum(results)
        total = len(results)

        print("\n" + "=" * 45)
        print("MILESTONE 3 TEST RESULTS")
        print("=" * 45)

        print(f"Passed: {passed}/{total}")
        print(f"Failed: {total - passed}/{total}")

        if passed == total:
            print("\nALL TESTS PASSED!")
        else:
            print("\nSOME TESTS FAILED. CHECK ABOVE.")

finally:
    # Close all connections before deleting the temporary DB.
    try:
        with test_app.app_context():
            db.session.remove()
            db.engine.dispose()
    except Exception as error:
        print("Database cleanup warning:", error)

    try:
        temp_dir.cleanup()
    except PermissionError:
        print(
            "Windows is still holding the temporary database. "
            "Close Python and remove the temporary folder later."
        )
