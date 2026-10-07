def login(client, username, password):
    return client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=True,
    )


def test_user_can_add_complete_and_delete_task(client, register_user):
    register_user("alice", "secret123")
    login(client, "alice", "secret123")

    add = client.post("/todos", data={"title": "Buy milk"}, follow_redirects=True)
    assert b"Buy milk" in add.data

    with client.application.app_context():
        todo = client.application.get_db().execute(
            "SELECT id, done FROM todos WHERE title = ?",
            ("Buy milk",),
        ).fetchone()
    assert todo["done"] == 0

    toggled = client.post(f"/todos/{todo['id']}/toggle", follow_redirects=True)
    assert toggled.status_code == 200
    with client.application.app_context():
        done = client.application.get_db().execute(
            "SELECT done FROM todos WHERE id = ?",
            (todo["id"],),
        ).fetchone()["done"]
    assert done == 1

    deleted = client.post(f"/todos/{todo['id']}/delete", follow_redirects=True)
    assert b"Buy milk" not in deleted.data


def test_users_only_see_their_own_tasks(client, register_user):
    register_user("alice", "secret123")
    login(client, "alice", "secret123")
    client.post("/todos", data={"title": "Alice private task"})
    client.post("/logout")

    register_user("bob", "secret123")
    login(client, "bob", "secret123")
    client.post("/todos", data={"title": "Bob grocery run"})

    bob_list = client.get("/")
    assert b"Bob grocery run" in bob_list.data
    assert b"Alice private task" not in bob_list.data

    with client.application.app_context():
        alice_todo = client.application.get_db().execute(
            "SELECT id FROM todos WHERE title = ?",
            ("Alice private task",),
        ).fetchone()

    client.post(f"/todos/{alice_todo['id']}/delete", follow_redirects=True)
    with client.application.app_context():
        still_there = client.application.get_db().execute(
            "SELECT id FROM todos WHERE id = ?",
            (alice_todo["id"],),
        ).fetchone()
    assert still_there is not None
