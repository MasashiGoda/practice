def test_non_admin_cannot_view_or_create_users(client):
    res = client.get("/admin/users")
    assert res.status_code == 403

    res = client.post("/admin/users", data={"username": "sneaky", "password": "xxxx"})
    assert res.status_code == 403


def test_non_admin_cannot_delete_users(client):
    res = client.post("/admin/users/1/delete")
    assert res.status_code == 403


def test_admin_can_create_a_regular_user_who_can_then_log_in(admin_client, raw_client):
    res = admin_client.post(
        "/admin/users", data={"username": "alice", "password": "alicepass"}
    )
    assert res.status_code == 302

    res = admin_client.get("/admin/users")
    body = res.data.decode()
    assert "alice" in body
    assert "一般" in body

    res = raw_client.post(
        "/login", data={"username": "alice", "password": "alicepass"}, follow_redirects=True
    )
    assert "ログアウト".encode() in res.data


def test_admin_cannot_create_duplicate_username(admin_client):
    admin_client.post("/admin/users", data={"username": "alice", "password": "alicepass"})
    res = admin_client.post(
        "/admin/users", data={"username": "alice", "password": "otherpass"}
    )
    assert res.status_code == 400
    assert "既に使われています".encode() in res.data


def test_admin_cannot_create_duplicate_of_admin_username(admin_client):
    res = admin_client.post(
        "/admin/users", data={"username": "admin", "password": "whatever1"}
    )
    assert res.status_code == 400
    assert "既に使われています".encode() in res.data


def test_regular_user_limit_of_ten_excludes_admin(admin_client):
    for i in range(10):
        res = admin_client.post(
            "/admin/users", data={"username": f"user{i}", "password": "password1"}
        )
        assert res.status_code == 302

    res = admin_client.post(
        "/admin/users", data={"username": "one_too_many", "password": "password1"}
    )
    assert res.status_code == 400
    assert "上限(10人)".encode() in res.data


def test_admin_can_delete_a_regular_user_and_their_todos(admin_client, raw_client):
    admin_client.post("/admin/users", data={"username": "bob", "password": "bobpass1"})
    raw_client.post("/login", data={"username": "bob", "password": "bobpass1"})
    raw_client.post("/todos", data={"title": "bobのタスク"})

    res = admin_client.get("/admin/users")
    bob_id = res.data.decode().split("/admin/users/")[1].split("/delete")[0]

    res = admin_client.post(f"/admin/users/{bob_id}/delete")
    assert res.status_code == 302

    res = admin_client.get("/admin/users")
    assert "bob" not in res.data.decode()

    # Slot is free again: re-creating "bob" should succeed.
    res = admin_client.post("/admin/users", data={"username": "bob", "password": "newpass1"})
    assert res.status_code == 302


def test_admin_cannot_delete_the_admin_account(admin_client):
    # admin is always the first user seeded by init_db(), so its id is 1
    # in a freshly created test database.
    res = admin_client.post("/admin/users/1/delete")
    assert res.status_code == 302

    res = admin_client.get("/admin/users")
    assert "admin" in res.data.decode()
    assert "管理者".encode() in res.data
