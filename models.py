from extensions import db 

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False) 
    student = db.relationship("Student", backref="user", uselist=False)

    examiner = db.relationship("Examiner", backref="user", uselist=False)


class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), unique=True, nullable=False)
    roll_number = db.Column(db.String(30), unique=True, nullable=False)
    department = db.Column(db.String(100), nullable=False)
    contact = db.Column(db.String(20), nullable=False)
    bookings = db.relationship("Booking", backref="student", lazy=True)

class Examiner(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), unique=True, nullable=False)
    department = db.Column(db.String(100), nullable=False)
    contact = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), default="pending", nullable=False)    
    slots = db.relationship("ExaminationSlot", backref="examiner", lazy=True)
    evaluations = db.relationship(
    "Evaluation",
    backref="examiner",
    lazy=True
    )

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default="active", nullable=False)
    examinations = db.relationship("Examination", backref="course", lazy=True)


class Examination(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    course_id = db.Column(
        db.Integer,
        db.ForeignKey("course.id"),
        nullable=False
    )

    name = db.Column(db.String(100), nullable=False)
    exam_type = db.Column(db.String(30), nullable=False)
    duration = db.Column(db.Integer, nullable=False)
    max_marks = db.Column(db.Integer, nullable=False)

    slot_creation_start = db.Column(db.DateTime)
    slot_creation_end = db.Column(db.DateTime)

    booking_start = db.Column(db.DateTime)
    booking_end = db.Column(db.DateTime)

    status = db.Column(db.String(30), default="Draft", nullable=False)    
    rubrics = db.relationship("ExaminationRubric", backref="examination", lazy=True)
    slots = db.relationship("ExaminationSlot", backref="examination", lazy=True)



class ExaminationRubric(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    exam_id = db.Column(
        db.Integer,
        db.ForeignKey("examination.id"),
        nullable=False
    )

    criterion_name = db.Column(db.String(100), nullable=False)
    max_marks = db.Column(db.Integer, nullable=False)
    weightage = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text)    

class ExaminationSlot(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    exam_id = db.Column(
        db.Integer,
        db.ForeignKey("examination.id"),
        nullable=False
    )

    examiner_id = db.Column(
        db.Integer,
        db.ForeignKey("examiner.id"),
        nullable=False
    )

    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)

    capacity = db.Column(db.Integer, nullable=False)
    available_seats = db.Column(db.Integer, nullable=False)

    status = db.Column(
        db.String(20),
        default="Available",
        nullable=False
    ) 
    bookings = db.relationship("Booking", backref="slot", lazy=True)
    
class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    student_id = db.Column(
        db.Integer,
        db.ForeignKey("student.id"),
        nullable=False
    )

    slot_id = db.Column(
        db.Integer,
        db.ForeignKey("examination_slot.id"),
        nullable=False
    )

    booking_date = db.Column(
        db.DateTime,
        default=db.func.current_timestamp()
    )

    status = db.Column(
        db.String(20),
        default="Booked",
        nullable=False
    ) 
    evaluation = db.relationship(
    "Evaluation",
    backref="booking",
    uselist=False,
    lazy=True
    )
   
class Evaluation(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    booking_id = db.Column(
        db.Integer,
        db.ForeignKey("booking.id"),
        unique=True,
        nullable=False
    )

    examiner_id = db.Column(
        db.Integer,
        db.ForeignKey("examiner.id"),
        nullable=False
    )

    marks = db.Column(db.Float, nullable=False)
    remarks = db.Column(db.Text)
    status = db.Column(db.String(20), default="Pending", nullable=False)          