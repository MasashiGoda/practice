import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

import app as app_module


@pytest.fixture
def _configured_app():
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    app_module.app.config["DATABASE"] = db_path
    app_module.app.config["TESTING"] = True
    app_module.init_db()

    yield app_module.app

    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def raw_client(_configured_app):
    # Plain (non-contextmanager) test clients so that using several clients
    # in the same test (e.g. an admin client and a regular-user client) does
    # not interleave and corrupt Flask's request-context stack.
    return _configured_app.test_client()


@pytest.fixture
def admin_client(_configured_app):
    client = _configured_app.test_client()
    client.post("/login", data={"username": "admin", "password": "admin"})
    return client


@pytest.fixture
def client(_configured_app, admin_client):
    admin_client.post(
        "/admin/users", data={"username": "testuser", "password": "testpass123"}
    )
    regular_client = _configured_app.test_client()
    regular_client.post(
        "/login", data={"username": "testuser", "password": "testpass123"}
    )
    return regular_client
