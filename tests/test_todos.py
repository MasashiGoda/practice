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


def test_completed_todo_appears_in_collapsible_section(client):
    client.post("/todos", data={"title": "牛乳を買う"})
    res = client.get("/")
    todo_id = res.data.decode().split('/todos/')[1].split('/toggle')[0]
    client.post(f"/todos/{todo_id}/toggle")

    res = client.get("/")
    body = res.data.decode()
    assert 'class="completed-section"' in body
    assert "完了済み (1件)" in body
    details_start = body.index('class="completed-section"')
    assert "牛乳を買う" in body[details_start:]


def test_no_completed_section_when_nothing_done(client):
    client.post("/todos", data={"title": "牛乳を買う"})
    res = client.get("/")
    body = res.data.decode()
    assert 'class="completed-section"' not in body
    assert "完了済み" not in body


def test_active_and_completed_lists_split_without_duplication(client):
    client.post("/todos", data={"title": "アクティブなタスク"})
    client.post("/todos", data={"title": "完了するタスク"})
    res = client.get("/")
    body = res.data.decode()
    done_id = body.split("完了するタスク")[0].split('/todos/')[-1].split('/toggle')[0]
    client.post(f"/todos/{done_id}/toggle")

    res = client.get("/")
    body = res.data.decode()
    details_start = body.index('class="completed-section"')
    before_details = body[:details_start]
    after_details_start = body[details_start:]

    assert "アクティブなタスク" in before_details
    assert "アクティブなタスク" not in after_details_start
    assert "完了するタスク" in after_details_start
    assert body.count("完了するタスク") == 1
    assert body.count("アクティブなタスク") == 1


def test_all_done_does_not_show_empty_message(client):
    client.post("/todos", data={"title": "牛乳を買う"})
    res = client.get("/")
    todo_id = res.data.decode().split('/todos/')[1].split('/toggle')[0]
    client.post(f"/todos/{todo_id}/toggle")

    res = client.get("/")
    body = res.data.decode()
    assert "タスクはまだありません" not in body
