import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///admin_assistant.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Microsoft Graph API OAuth settings
    MS_CLIENT_ID = os.environ.get('MS_CLIENT_ID')
    MS_CLIENT_SECRET = os.environ.get('MS_CLIENT_SECRET')
    MS_TENANT_ID = os.environ.get('MS_TENANT_ID')
    MS_REDIRECT_URI = os.environ.get('MS_REDIRECT_URI', 'http://localhost:5000/ms365/auth/callback') 