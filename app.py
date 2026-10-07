import os
import sqlite3
from functools import wraps
from pathlib import Path

from dotenv import load_dotenv
from flask import (
    Flask,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)

    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-only-change-me"),
        DATABASE=os.environ.get("DATABASE_PATH", "/tmp/todo.db"),
    )

    if test_config:
        app.config.update(test_config)

    def get_db():
        if "db" not in g:
            g.db = sqlite3.connect(
                app.config["DATABASE"],
                detect_types=sqlite3.PARSE_DECLTYPES,
            )
            g.db.row_factory = sqlite3.Row
            g.db.execute("PRAGMA foreign_keys = ON")
        return g.db

    def close_db(_e=None):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    def init_db():
        db = get_db()
        with open(BASE_DIR / "schema.sql", encoding="utf-8") as schema_file:
            db.executescript(schema_file.read())

    app.get_db = get_db
    app.init_db = init_db
    app.teardown_appcontext(close_db)

    with app.app_context():
        if not Path(app.config["DATABASE"]).exists():
            init_db()

    def login_required(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if session.get("user_id") is None:
                return redirect(url_for("login"))
            return view(*args, **kwargs)

        return wrapped

    def current_user():
        user_id = session.get("user_id")
        if user_id is None:
            return None
        return get_db().execute(
            "SELECT id, username FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            username = (request.form.get("username") or "").strip()
            password = request.form.get("password") or ""
            error = None

            if not username:
                error = "Username is required."
            elif not password:
                error = "Password is required."
            else:
                db = get_db()
                existing = db.execute(
                    "SELECT id FROM users WHERE username = ?",
                    (username,),
                ).fetchone()
                if existing:
                    error = "That username is already taken."
                else:
                    db.execute(
                        "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                        (username, generate_password_hash(password, method="pbkdf2:sha256")),
                    )
                    db.commit()
                    flash("Account created. Sign in to continue.")
                    return redirect(url_for("login"))

            flash(error)

        return render_template("register.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = (request.form.get("username") or "").strip()
            password = request.form.get("password") or ""
            db = get_db()
            user = db.execute(
                "SELECT id, username, password_hash FROM users WHERE username = ?",
                (username,),
            ).fetchone()

            if user is None or not check_password_hash(user["password_hash"], password):
                flash("Invalid username or password.")
            else:
                session.clear()
                session["user_id"] = user["id"]
                return redirect(url_for("todo_list"))

        return render_template("login.html")

    @app.post("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.route("/")
    @login_required
    def todo_list():
        db = get_db()
        todos = db.execute(
            """
            SELECT id, title, done, created_at
            FROM todos
            WHERE user_id = ?
            ORDER BY created_at DESC, id DESC
            """,
            (session["user_id"],),
        ).fetchall()
        return render_template("todos.html", todos=todos, user=current_user())

    @app.post("/todos")
    @login_required
    def add_todo():
        title = (request.form.get("title") or "").strip()
        if not title:
            flash("Task title is required.")
            return redirect(url_for("todo_list"))

        db = get_db()
        db.execute(
            "INSERT INTO todos (user_id, title) VALUES (?, ?)",
            (session["user_id"], title),
        )
        db.commit()
        return redirect(url_for("todo_list"))

    def owned_todo(todo_id):
        return get_db().execute(
            "SELECT id FROM todos WHERE id = ? AND user_id = ?",
            (todo_id, session["user_id"]),
        ).fetchone()

    @app.post("/todos/<int:todo_id>/toggle")
    @login_required
    def toggle_todo(todo_id):
        if owned_todo(todo_id) is None:
            flash("Task not found.")
            return redirect(url_for("todo_list"))

        db = get_db()
        db.execute(
            "UPDATE todos SET done = CASE WHEN done = 1 THEN 0 ELSE 1 END WHERE id = ? AND user_id = ?",
            (todo_id, session["user_id"]),
        )
        db.commit()
        return redirect(url_for("todo_list"))

    @app.post("/todos/<int:todo_id>/delete")
    @login_required
    def delete_todo(todo_id):
        if owned_todo(todo_id) is None:
            flash("Task not found.")
            return redirect(url_for("todo_list"))

        db = get_db()
        db.execute(
            "DELETE FROM todos WHERE id = ? AND user_id = ?",
            (todo_id, session["user_id"]),
        )
        db.commit()
        return redirect(url_for("todo_list"))

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
