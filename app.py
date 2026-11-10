from flask import Flask , render_template , request , redirect , url_for  
from flask_sqlalchemy import SQLAlchemy
from extensions import db

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///examination.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False    

db.init_app(app)

@app.route("/")
def home():
    return render_template("home.html")



if __name__ == "__main__":
    with app.app_context():
        from models import *
        db.create_all()
        print("Database tables created successfully.")
        print("All models and relationships loaded successfully.")


    app.run(debug=True)