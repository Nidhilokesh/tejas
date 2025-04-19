# auth_models.py
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# —— Single, shared SQLAlchemy instance ——
db = SQLAlchemy()

class UserAuth(UserMixin, db.Model):
    __tablename__ = 'user_auth'
    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    def set_password(self, pw):
        self.password_hash = generate_password_hash(pw)

    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)


class UserProfile(db.Model):
    __tablename__ = 'user_profile'
    id      = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user_auth.id'), unique=True, nullable=False)
    name    = db.Column(db.String(100), nullable=False)
    age     = db.Column(db.Integer, nullable=False)
    sex     = db.Column(db.String(10), nullable=False)
    email   = db.Column(db.String(120), unique=True, nullable=False)

    user = db.relationship('UserAuth', backref=db.backref('profile', uselist=False))
