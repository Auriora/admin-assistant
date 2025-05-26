import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# Initialize SQLAlchemy (instance will be used in models.py)
db = SQLAlchemy()
migrate = Migrate()

def create_app():
    app = Flask(__name__)
    env = os.environ.get('APP_ENV', 'development').lower()
    if env == 'production':
        app.config.from_object('app.config.ProductionConfig')
    elif env == 'testing':
        app.config.from_object('app.config.TestingConfig')
    else:
        app.config.from_object('app.config.DevelopmentConfig')

    db.init_app(app)
    migrate.init_app(app, db)

    # Logging setup
    log_level = app.config.get('LOG_LEVEL', 'WARNING').upper()
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    file_handler = RotatingFileHandler(os.path.join(log_dir, 'app.log'), maxBytes=10240, backupCount=5)
    file_handler.setFormatter(logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s: %(message)s [%(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(log_level)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
    ))
    console_handler.setLevel(log_level)
    app.logger.setLevel(log_level)
    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)

    # Log request info
    @app.before_request
    def log_request_info():
        app.logger.info(f"Request: {request.method} {request.path} from {request.remote_addr}")

    # Import and register blueprints
    from app.routes.main import main_bp
    app.register_blueprint(main_bp)

    return app 