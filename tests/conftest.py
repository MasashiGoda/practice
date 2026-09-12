import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

import app as app_module


@pytest.fixture
def client():
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    app_module.app.config["DATABASE"] = db_path
    app_module.app.config["TESTING"] = True
    app_module.init_db()

    with app_module.app.test_client() as client:
        yield client

    Path(db_path).unlink(missing_ok=True)
