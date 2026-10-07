import os
import tempfile

import pytest

from app import create_app


@pytest.fixture
def app():
    fd, db_path = tempfile.mkstemp(suffix=".db")
    application = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "DATABASE": db_path,
        }
    )
    yield application
    os.close(fd)
    os.unlink(db_path)


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def register_user(client):
    def _register(username="alice", password="secret123"):
        return client.post(
            "/register",
            data={"username": username, "password": password},
            follow_redirects=True,
        )

    return _register
