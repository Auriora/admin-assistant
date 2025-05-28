import pytest
from app import create_app

def test_app_factory():
    app = create_app()
    assert app is not None
    assert app.config['SQLALCHEMY_DATABASE_URI'].startswith('sqlite') 