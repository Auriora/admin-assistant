import logging
import os
from logging.handlers import RotatingFileHandler

from flask import Flask, request
from flask_apscheduler import APScheduler
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

from core.services.background_job_service import BackgroundJobService
from core.services.scheduled_archive_service import ScheduledArchiveService
from web.app.services import msgraph

try:
    import opentelemetry.sdk.trace as sdk_trace
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import \
        OTLPSpanExporter
    from opentelemetry.instrumentation.flask import FlaskInstrumentor
    from opentelemetry.sdk.resources import SERVICE_NAME, Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False

# Initialize SQLAlchemy (instance will be used in models.py)
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()


def create_app():
    app = Flask(__name__)
    env = os.environ.get("APP_ENV", "development").lower()
    if env == "production":
        app.config.from_object("web.app.config.ProductionConfig")
    elif env == "testing":
        app.config.from_object("web.app.config.TestingConfig")
    else:
        app.config.from_object("web.app.config.DevelopmentConfig")

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = "main.login"  # type: ignore[attr-defined]

    # --- OpenTelemetry Tracing Setup ---
    if OTEL_AVAILABLE:
        resource = Resource(attributes={SERVICE_NAME: "admin-assistant"})
        provider = TracerProvider(resource=resource)
        trace.set_tracer_provider(provider)
        otlp_exporter = OTLPSpanExporter()
        span_processor = BatchSpanProcessor(otlp_exporter)
        provider.add_span_processor(span_processor)
        FlaskInstrumentor().instrument_app(app)
        tracer = trace.get_tracer(__name__)
    else:
        tracer = None
    # --- End OpenTelemetry Setup ---

    # --- Flask-APScheduler Setup ---
    scheduler = APScheduler()
    scheduler.init_app(app)
    scheduler.start()

    # Initialize background job services
    background_job_service = BackgroundJobService(scheduler)
    scheduled_archive_service = ScheduledArchiveService(background_job_service)

    # Store services in app context for access in routes
    app.background_job_service = background_job_service
    app.scheduled_archive_service = scheduled_archive_service

    # Auto-schedule jobs for all active users on startup (optional)
    # Uncomment the following lines to enable automatic scheduling on startup
    # try:
    #     with app.app_context():
    #         scheduled_archive_service.schedule_all_active_users(schedule_type='daily', hour=23, minute=59)
    #         app.logger.info("Auto-scheduled archive jobs for all active users")
    # except Exception as e:
    #     app.logger.error(f"Failed to auto-schedule archive jobs: {e}")

    # --- End Scheduler Setup ---

    # Logging setup
    log_level = app.config.get("LOG_LEVEL", "WARNING").upper()
    log_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs"
    )
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, "app.log"), maxBytes=10240, backupCount=5
    )
    file_handler.setFormatter(
        logging.Formatter(
            "[%(asctime)s] %(levelname)s in %(module)s: %(message)s [%(pathname)s:%(lineno)d]"
        )
    )
    file_handler.setLevel(log_level)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(
        logging.Formatter("[%(asctime)s] %(levelname)s in %(module)s: %(message)s")
    )
    console_handler.setLevel(log_level)
    app.logger.setLevel(log_level)
    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)

    # Security headers middleware
    @app.after_request
    def add_security_headers(response):
        """Add security headers to all responses."""
        # Content Security Policy
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            "img-src 'self' data: https:; "
            "font-src 'self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            "connect-src 'self' https://graph.microsoft.com; "
            "frame-ancestors 'none';"
        )

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=()"
        )

        # HTTPS enforcement in production
        if not request.is_secure and os.environ.get("APP_ENV") == "production":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )

        return response

    # Log request info
    @app.before_request
    def log_request_info():
        app.logger.info(
            f"Request: {request.method} {request.path} from {request.remote_addr}"
        )
        # Example custom span for request
        if tracer:
            with tracer.start_as_current_span("log_request_info"):
                pass

    # Import and register blueprints
    from web.app.routes.main import main_bp

    app.register_blueprint(main_bp)

    @login_manager.user_loader
    def load_user(user_id):
        from web.app.models import User

        return User.query.get(int(user_id))

    return app
