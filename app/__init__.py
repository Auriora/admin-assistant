import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# Initialize SQLAlchemy (instance will be used in models.py)
db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    app.config.from_object('app.config.Config')

    db.init_app(app)

    # Import and register blueprints
    from app.routes.main import main_bp
    app.register_blueprint(main_bp)

    return app 