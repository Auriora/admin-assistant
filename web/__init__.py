# flask/__init__.py

import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_apscheduler import APScheduler
from core.services.scheduled_archive_job import scheduled_archive_job
from web.app.services import msgraph
from web.app.config import Config
try:
    from opentelemetry import trace
    from opentelemetry.sdk.resources import SERVICE_NAME, Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.flask import FlaskInstrumentor
    import opentelemetry.sdk.trace as sdk_trace
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False

# Initialize SQLAlchemy (instance will be used in models.py)
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()

def create_app():
    web_app = Flask(__name__)
    env = os.environ.get('APP_ENV', 'development').lower()
    if env == 'production':
        web_app.config.from_object(Config.ProductionConfig)
    elif env == 'testing':
        web_app.config.from_object(Config.TestingConfig)
    else:
        web_app.config.from_object(Config.DevelopmentConfig)

    db.init_app(web_app)
    migrate.init_app(web_app, db)
    login_manager.init_app(web_app)
    login_manager.login_view = 'main.login'  # type: ignore[attr-defined]

    # --- OpenTelemetry Tracing Setup ---
    if OTEL_AVAILABLE:
        resource = Resource(attributes={SERVICE_NAME: "admin-assistant"})
        provider = TracerProvider(resource=resource)
        trace.set_tracer_provider(provider)
        otlp_exporter = OTLPSpanExporter()
        span_processor = BatchSpanProcessor(otlp_exporter)
        provider.add_span_processor(span_processor)
        FlaskInstrumentor().instrument_app(web_app)
        tracer = trace.get_tracer(__name__)
    else:
        tracer = None
    # --- End OpenTelemetry Setup ---

    # --- Flask-APScheduler Setup ---
    scheduler = APScheduler()
    scheduler.init_app(web_app)
    scheduler.start()
    # Schedule the archive job to run daily at 23:59 UTC
    scheduler.add_job(
        id='daily_archive',
        func=lambda: scheduled_archive_job(db, db.models['User'], msgraph.get_authenticated_session_for_user, web_app.logger),
        trigger='cron',
        hour=23,
        minute=59
    )
    # --- End Scheduler Setup ---

    # Logging setup
    log_level = web_app.config.get('LOG_LEVEL', 'WARNING').upper()
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
    web_app.logger.setLevel(log_level)
    web_app.logger.addHandler(file_handler)
    web_app.logger.addHandler(console_handler)

    # Log request info
    @web_app.before_request
    def log_request_info():
        web_app.logger.info(f"Request: {request.method} {request.path} from {request.remote_addr}")
        # Example custom span for request
        if tracer:
            with tracer.start_as_current_span("log_request_info"):
                pass

    # Import and register blueprints
    from web.app.routes.main import main_bp
    web_app.register_blueprint(main_bp)

    @login_manager.user_loader
    def load_user(user_id):
        from web.app.models import User
        return User.query.get(int(user_id))

    return web_app