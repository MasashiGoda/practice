import secrets
import sqlite3
from functools import wraps
from pathlib import Path

from flask import Flask, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

DB_PATH = Path(__file__).parent / "todo.db"
MAX_REGULAR_USERS = 10

app = Flask(__name__)
app.config.setdefault("DATABASE", str(DB_PATH))
app.secret_key = secrets.token_hex(32)

# Used to keep login timing independent of whether the username exists,
# so check_password_hash always runs the same scrypt work either way.
_DUMMY_PASSWORD_HASH = generate_password_hash(secrets.token_hex(16))


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    with sqlite3.connect(app.config["DATABASE"]) as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                is_admin INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS todos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                title TEXT NOT NULL,
                done INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                planned_date TEXT,
                due_date TEXT
            )
            """
        )
        admin_row = db.execute(
            "SELECT id FROM users WHERE username = ?", ("admin",)
        ).fetchone()
        if admin_row is None:
            default_password = "admin"  # nosec B106 -- 練習用ローカルアプリの初期管理者パスワード。ユーザー指示による固定値
            db.execute(
                "INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, 1)",
                ("admin", generate_password_hash(default_password)),
            )


@app.before_request
def load_logged_in_user():
    user_id = session.get("user_id")
    g.user = None
    if user_id is not None:
        g.user = get_db().execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        ).fetchone()


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped_view


def admin_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("login"))
        if not g.user["is_admin"]:
            return "Forbidden", 403
        return view(*args, **kwargs)

    return wrapped_view


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        password_hash = user["password_hash"] if user else _DUMMY_PASSWORD_HASH
        if user is None or not check_password_hash(password_hash, password):
            error = "ユーザー名またはパスワードが正しくありません"
        else:
            session.clear()
            session["user_id"] = user["id"]
            return redirect(url_for("index"))
    return render_template("login.html", error=error)


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))


def _all_users(db):
    return db.execute("SELECT * FROM users ORDER BY is_admin DESC, id ASC").fetchall()


@app.route("/admin/users", methods=["GET"])
@admin_required
def admin_users():
    db = get_db()
    return render_template("admin_users.html", users=_all_users(db), error=None)


@app.route("/admin/users", methods=["POST"])
@admin_required
def create_user():
    db = get_db()
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    error = None
    if not username or len(password) < 4:
        error = "ユーザー名と4文字以上のパスワードを入力してください"
    elif db.execute(
        "SELECT id FROM users WHERE username = ?", (username,)
    ).fetchone():
        error = "そのユーザー名は既に使われています"
    else:
        regular_count = db.execute(
            "SELECT COUNT(*) AS count FROM users WHERE is_admin = 0"
        ).fetchone()["count"]
        if regular_count >= MAX_REGULAR_USERS:
            error = "登録できる一般ユーザー数の上限(10人)に達しています"

    if error:
        return render_template("admin_users.html", users=_all_users(db), error=error), 400

    db.execute(
        "INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, 0)",
        (username, generate_password_hash(password)),
    )
    db.commit()
    return redirect(url_for("admin_users"))


@app.route("/admin/users/<int:user_id>/delete", methods=["POST"])
@admin_required
def delete_user(user_id):
    db = get_db()
    target = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if target is not None and not target["is_admin"]:
        db.execute("DELETE FROM todos WHERE user_id = ?", (user_id,))
        db.execute("DELETE FROM users WHERE id = ?", (user_id,))
        db.commit()
    return redirect(url_for("admin_users"))


@app.route("/")
@login_required
def index():
    db = get_db()
    todos = db.execute(
        "SELECT * FROM todos WHERE user_id = ? ORDER BY done ASC, id DESC",
        (g.user["id"],),
    ).fetchall()
    return render_template("index.html", todos=todos)


@app.route("/todos", methods=["POST"])
@login_required
def create_todo():
    title = request.form.get("title", "").strip()
    if title:
        planned_date = request.form.get("planned_date", "").strip() or None
        due_date = request.form.get("due_date", "").strip() or None
        db = get_db()
        db.execute(
            "INSERT INTO todos (user_id, title, planned_date, due_date) VALUES (?, ?, ?, ?)",
            (g.user["id"], title, planned_date, due_date),
        )
        db.commit()
    return redirect(url_for("index"))


@app.route("/todos/<int:todo_id>/toggle", methods=["POST"])
@login_required
def toggle_todo(todo_id):
    db = get_db()
    db.execute(
        "UPDATE todos SET done = 1 - done WHERE id = ? AND user_id = ?",
        (todo_id, g.user["id"]),
    )
    db.commit()
    return redirect(url_for("index"))


@app.route("/todos/<int:todo_id>/delete", methods=["POST"])
@login_required
def delete_todo(todo_id):
    db = get_db()
    db.execute(
        "DELETE FROM todos WHERE id = ? AND user_id = ?", (todo_id, g.user["id"])
    )
    db.commit()
    return redirect(url_for("index"))


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)  # nosec B201 -- ローカル練習用アプリ、本番運用しない
