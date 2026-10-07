def test_register_then_login(client, register_user):
    register_user("alice", "secret123")
    response = client.post(
        "/login",
        data={"username": "alice", "password": "secret123"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Your tasks" in response.data
    assert b"alice" in response.data


def test_login_rejects_wrong_password(client, register_user):
    register_user("alice", "secret123")
    response = client.post(
        "/login",
        data={"username": "alice", "password": "wrong"},
        follow_redirects=True,
    )
    assert b"Invalid username or password." in response.data
    assert b"Your tasks" not in response.data


def test_unauthenticated_home_redirects_to_login(client):
    response = client.get("/")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_password_is_stored_hashed(app, register_user):
    register_user("alice", "secret123")
    with app.app_context():
        row = app.get_db().execute(
            "SELECT password_hash FROM users WHERE username = ?",
            ("alice",),
        ).fetchone()
    assert row is not None
    assert row["password_hash"] != "secret123"
    assert row["password_hash"].startswith("scrypt:") or row["password_hash"].startswith(
        "pbkdf2:"
    )
