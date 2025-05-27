import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///admin_assistant.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Microsoft Graph API OAuth settings
    MS_CLIENT_ID = os.environ.get('MS_CLIENT_ID', 'e255aab8-b12b-434f-ba9c-979f06b46fc0')
    MS_CLIENT_SECRET = os.environ.get('MS_CLIENT_SECRET')
    MS_TENANT_ID = os.environ.get('MS_TENANT_ID', 'consumers')
    MS_REDIRECT_URI = os.environ.get('MS_REDIRECT_URI', 'http://localhost:5000/ms365/auth/callback')
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'WARNING')
    DEBUG = False

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL', 'sqlite:///admin_assistant_flask_dev.db')
    LOG_LEVEL = os.environ.get('DEV_LOG_LEVEL', 'DEBUG')

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL', 'sqlite:///admin_assistant_flask_test.db')
    LOG_LEVEL = os.environ.get('TEST_LOG_LEVEL', 'INFO')

class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.environ.get('PROD_DATABASE_URL', 'sqlite:///admin_assistant_flask_prod.db')
    LOG_LEVEL = os.environ.get('PROD_LOG_LEVEL', 'WARNING') 