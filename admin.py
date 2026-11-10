from app import app
from extensions import db
from models import User
from werkzeug.security import generate_password_hash

with app.app_context():

    db.create_all()

    existing_admin = User.query.filter_by(role="admin").first()
    if existing_admin:
        print(existing_admin.full_name, existing_admin.email, existing_admin.role)
        print("Admin already exists.")

    else:
        name = input("Enter admin full name: ")    
        email = input("Enter admin email: ")
        password = input("Enter admin password: ")

        admin_user = User(
            full_name=name,
            email=email,
            password=generate_password_hash(password),
            role="admin"
        )
        db.session.add(admin_user)
        db.session.commit()

        print("Admin account created successfully.")
