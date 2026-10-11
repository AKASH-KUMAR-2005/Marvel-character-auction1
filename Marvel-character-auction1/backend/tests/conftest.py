import os
import tempfile
import pytest
from app import create_app
from app.models import db

@pytest.fixture
def app(tmp_path):
    db_path = tmp_path / "test_marvel.sqlite"
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path.as_posix()}",
        "WIKIPEDIA_LOOKUP_ENABLED": False,
        "AI_PROVIDER": "offline",
        "FRONTEND_ORIGIN": "http://localhost:5173",
    })
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()
