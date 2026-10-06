from flask import Flask , render_template, request, redirect, session
from .config import Config
from .extensions import db, migrate, bcrypt

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)

    from .models import User, Product
    with app.app_context():
        db.create_all()

    return app