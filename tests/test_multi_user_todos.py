def _new_logged_in_client(app_module_client_factory, admin_client, username, password):
    admin_client.post("/admin/users", data={"username": username, "password": password})
    new_client = app_module_client_factory()
    new_client.post("/login", data={"username": username, "password": password})
    return new_client


def test_users_only_see_their_own_todos(_configured_app, admin_client):
    def make_client(username, password):
        return _new_logged_in_client(
            _configured_app.test_client, admin_client, username, password
        )

    alice = make_client("alice", "alicepass1")
    bob = make_client("bob", "bobpass1")

    alice.post("/todos", data={"title": "アリスのタスク"})
    bob.post("/todos", data={"title": "ボブのタスク"})

    alice_body = alice.get("/").data.decode()
    assert "アリスのタスク" in alice_body
    assert "ボブのタスク" not in alice_body

    bob_body = bob.get("/").data.decode()
    assert "ボブのタスク" in bob_body
    assert "アリスのタスク" not in bob_body


def test_user_cannot_toggle_or_delete_another_users_todo(_configured_app, admin_client):
    def make_client(username, password):
        return _new_logged_in_client(
            _configured_app.test_client, admin_client, username, password
        )

    alice = make_client("alice", "alicepass1")
    bob = make_client("bob", "bobpass1")

    alice.post("/todos", data={"title": "アリスのタスク"})
    alice_body = alice.get("/").data.decode()
    alice_todo_id = alice_body.split("/todos/")[1].split("/toggle")[0]

    bob.post(f"/todos/{alice_todo_id}/toggle")
    alice_body_after_toggle = alice.get("/").data.decode()
    assert 'class="done"' not in alice_body_after_toggle

    bob.post(f"/todos/{alice_todo_id}/delete")
    alice_body_after_delete = alice.get("/").data.decode()
    assert "アリスのタスク" in alice_body_after_delete
