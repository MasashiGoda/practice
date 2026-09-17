def test_default_admin_exists_and_can_log_in(raw_client):
    res = raw_client.post(
        "/login", data={"username": "admin", "password": "admin"}, follow_redirects=True
    )
    assert res.status_code == 200
    assert "ログアウト".encode() in res.data


def test_login_fails_with_wrong_password(raw_client):
    res = raw_client.post(
        "/login",
        data={"username": "admin", "password": "wrong"},
        follow_redirects=True,
    )
    assert "ユーザー名またはパスワードが正しくありません".encode() in res.data


def test_login_fails_with_unknown_username(raw_client):
    res = raw_client.post(
        "/login",
        data={"username": "nobody", "password": "whatever"},
        follow_redirects=True,
    )
    assert "ユーザー名またはパスワードが正しくありません".encode() in res.data


def test_protected_routes_redirect_to_login_when_logged_out(raw_client):
    for path, method in [
        ("/", "get"),
        ("/todos", "post"),
        ("/todos/1/toggle", "post"),
        ("/todos/1/delete", "post"),
        ("/admin/users", "get"),
    ]:
        res = getattr(raw_client, method)(path)
        assert res.status_code == 302
        assert res.headers["Location"].endswith("/login")


def test_admin_users_post_redirects_to_login_when_logged_out(raw_client):
    res = raw_client.post("/admin/users", data={"username": "x", "password": "xxxx"})
    assert res.status_code == 302
    assert res.headers["Location"].endswith("/login")


def test_logout_clears_session(admin_client):
    admin_client.post("/logout")
    res = admin_client.get("/")
    assert res.status_code == 302
    assert res.headers["Location"].endswith("/login")
