from app import app
from models import User, Course

with app.app_context():

    users = User.query.all()

    print("Users:")
    for user in users:
        print(user.email, user.role)

    print("Total courses:", Course.query.count())