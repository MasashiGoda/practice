def test_index_shows_empty_state(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "タスクはまだありません".encode() in res.data


def test_create_todo_adds_it_to_the_list(client):
    client.post("/todos", data={"title": "牛乳を買う"})
    res = client.get("/")
    assert "牛乳を買う".encode() in res.data


def test_create_todo_ignores_blank_title(client):
    client.post("/todos", data={"title": "   "})
    res = client.get("/")
    assert "タスクはまだありません".encode() in res.data


def test_toggle_todo_marks_it_done(client):
    client.post("/todos", data={"title": "牛乳を買う"})
    res = client.get("/")
    todo_id = res.data.decode().split('/todos/')[1].split('/toggle')[0]

    client.post(f"/todos/{todo_id}/toggle")
    res = client.get("/")
    assert 'class="done"' in res.data.decode()


def test_delete_todo_removes_it(client):
    client.post("/todos", data={"title": "牛乳を買う"})
    res = client.get("/")
    todo_id = res.data.decode().split('/todos/')[1].split('/toggle')[0]

    client.post(f"/todos/{todo_id}/delete")
    res = client.get("/")
    assert "牛乳を買う".encode() not in res.data


def test_create_todo_with_dates_shows_them_in_list(client):
    client.post(
        "/todos",
        data={
            "title": "牛乳を買う",
            "planned_date": "2026-09-20",
            "due_date": "2026-09-25",
        },
    )
    res = client.get("/")
    body = res.data.decode()
    assert "計画: 2026-09-20" in body
    assert "期限: 2026-09-25" in body


def test_create_todo_without_dates_shows_no_dates(client):
    client.post("/todos", data={"title": "牛乳を買う"})
    res = client.get("/")
    body = res.data.decode()
    assert "牛乳を買う" in body
    assert "計画:" not in body
    assert "期限:" not in body
