# 0001: 計画日・期限日の追加

## 依頼内容

TODOに「計画した日」(いつやる予定か)と「期限日」(締め切り)を追加したい。

## 現状把握

- `app.py`: Flask + SQLite。`todos` テーブルは `id`, `title`, `done`, `created_at` のみ。
  `created_at` はレコード作成時刻の自動記録で、今回追加したい「計画日」「期限日」(ユーザーが入力する予定日・締切日)とは別物。
- `init_db()` は `CREATE TABLE IF NOT EXISTS` のみで、既存テーブルへの列追加(マイグレーション)の仕組みがない。
  リポジトリ直下に既存の `todo.db` が存在するが、中身は破棄してよいとの確認済み(承認コメント参照)のため、マイグレーションは不要。
- `templates/index.html`: 追加フォーム(タイトルのみ)、一覧(チェックボタン・タイトル・削除ボタン)。日付の入力欄・表示欄はまだない。
- `tests/test_todos.py`: 一覧表示・追加・完了切替・削除の基本テストのみ。日付関連のテストはまだない。
- 一覧の並び順は `ORDER BY done ASC, id DESC`(未完了が先、新しい順)。

## 実装方針

1. **データモデル変更**(`app.py`)
   - `todos` テーブルの `CREATE TABLE IF NOT EXISTS` 定義に、最初から `planned_date TEXT`(計画日)と `due_date TEXT`(期限日)を追加する。どちらも空欄可(NULL許容)。値は `YYYY-MM-DD` 形式の文字列で保存する(HTML5 `<input type="date">` の値をそのまま使う)。
   - 既存の `todo.db` は開発用データのため実装時に削除し、新しいスキーマで作り直す(マイグレーション処理は実装しない)。
   - `create_todo()`: `request.form.get("planned_date")` / `get("due_date")` を読み、空文字なら `None` としてINSERTする。

2. **UI変更**(`templates/index.html`, `static/style.css`)
   - 追加フォーム(`.add-form`)に `<input type="date" name="planned_date">`(計画日)と `<input type="date" name="due_date">`(期限日)を追加。両方とも任意入力(`required` は付けない)。
   - 一覧の各項目(`<li>`)で、`planned_date` または `due_date` が設定されていれば、タイトルの下に小さく「計画: 2026-09-20 / 期限: 2026-09-25」のような表示を追加する。両方とも未設定なら何も表示しない。
   - `static/style.css` に日付表示用のクラス(例: `.dates`)を追加し、`--muted` カラーで既存のトーン&マナーに合わせる。
   - UI変更があるため、実装後に `/design-audit` が必要。

## スコープ外

- 作成済みタスクの計画日・期限日を後から編集する機能(現状トグル・削除以外の更新UIが無いため、今回は作成時のみ設定可能とする)。
- 期限超過タスクの強調表示(赤字など)。
- 計画日・期限日によるソート・フィルタ機能。
- 日付の妥当性チェック(例: 期限日が計画日より前、などのバリデーション)。

## テスト方針

- `tests/test_todos.py` に追加:
  - 計画日・期限日を指定してタスクを作成すると、一覧にその日付が表示されること。
  - 日付を指定せずにタスクを作成しても、これまで通り正常に動作し、日付表示が出ないこと(既存の空文字送信時と同様、日付欄が空でもエラーにならないこと)。
- 既存テストがすべて引き続き通ることを確認する(`PYTHONPATH=./vendor python3 -m pytest tests/ -q`)。

## 承認コメント

- 既存の `todo.db` のデータは一度破棄してよい。そのためマイグレーション(`PRAGMA table_info` での列存在チェック + `ALTER TABLE`)は不要にして良く、`CREATE TABLE` のスキーマ定義に `planned_date` / `due_date` を最初から含める形にシンプル化できる。→ 対応済み。`実装方針` からマイグレーション処理を削除し、既存 `todo.db` を削除して作り直す方針に更新した。

## 実装メモ

- 変更ファイル: `app.py`, `templates/index.html`, `static/style.css`
- `todos` テーブルの `CREATE TABLE IF NOT EXISTS` に `planned_date TEXT`, `due_date TEXT` を追加(マイグレーションなし、方針通り)。
- 開発用の既存 `todo.db` は削除済み(次回起動時に新スキーマで再作成される)。
- `create_todo()` で `planned_date` / `due_date` を読み取り、空文字は `None` としてINSERT。
- 追加フォームに `<input type="date">` を2つ追加(`required` なし、任意入力)。
- 一覧の `<li>` 内でタイトルと日付表示をまとめる `.content` div を新設(元々 `.title` に付いていた `flex: 1` を `.content` に移動)。両方の日付が未設定なら `.dates` ごと非表示。
- `.add-form` はテキスト欄を1行目、日付欄を2行目に折り返す `flex-wrap` レイアウトに変更(狭い画面でも崩れないように)。
- 既存テスト(`tests/test_todos.py`)は変更なしで5件すべて通過を確認済み。日付関連のテストは次の `/test` ステップで追加する。

## ステータス: 実装完了(2026-09-13)
