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

## テスト結果

- 実行コマンド: `PYTHONPATH=./vendor python3 -m pytest tests/ -q`
- 追加テスト(`tests/test_todos.py`):
  - `test_create_todo_with_dates_shows_them_in_list` — 計画日・期限日を指定して作成すると一覧に「計画: 2026-09-20」「期限: 2026-09-25」が表示されること
  - `test_create_todo_without_dates_shows_no_dates` — 日付未指定でも従来通り動作し、「計画:」「期限:」が表示されないこと
- 結果: 既存5件 + 新規2件 = **7 passed**(実装は前ステップで完了済みのため、今回はGreenのまま新規テストを追加して確認する形になった)

## デザイン監査

- 差分対象: `templates/index.html`, `static/style.css`
- 指摘・修正: 追加フォームの日付欄が `aria-label` のみで、見た目のラベルがなかった(`type="date"` は多くのブラウザで `placeholder` が効かないため、計画日/期限日の区別が画面上つきにくい)。`<label class="date-field">計画日/期限日<input type="date">...</label>` に修正し、見た目のラベルを追加。修正後、既存テスト7件は引き続き全て通過を確認済み。
- ユーザーに実機(`PYTHONPATH=./vendor python3 app.py`)で以下を確認してもらい、OKを確認:
  - モバイル幅(~400px)でのレイアウト崩れなし
  - ライト/ダーク両方での視認性(「計画:」「期限:」のミュートカラー含む)
  - 日付ありタスクの表示、日付なしタスクで余計な表示が出ないこと
  - 長いタイトルの折り返し
- 静的確認(コードレビューベース):
  - 区切り「/」は両方の日付がある場合のみ挿入されるロジックのため、片方欠落時の不要な記号なし
  - `overflow-wrap: break-word` により長いタイトルの表示崩れなし
  - 既存の余白・角丸・配色トーンを踏襲

## レビュー

- 対象: `feature/0001-task-dates` と `master` の全差分(`app.py`, `templates/index.html`, `static/style.css`, `tests/test_todos.py`)
- 正しさ: SQLはパラメータ化済みでインジェクションの懸念なし。空文字→`None`変換、日付表示の区切り「/」ロジック(両方揃った時のみ挿入)いずれも意図通り動作する実装になっている。
- 計画との整合性: `## 実装方針` に書かれた内容(テーブル列追加・フォーム入力欄・一覧表示・スタイル)のみが実装されており、逸脱なし。
- スコープ外の遵守: 「編集機能」「期限超過の強調表示」「ソート・フィルタ」「日付の妥当性チェック」のいずれにも手を出していないことを確認。
- テストの実効性: `test_create_todo_with_dates_shows_them_in_list` / `test_create_todo_without_dates_shows_no_dates` は実際にレスポンス本文の文字列を検証しており、形だけのテストではない。承認済みの `## テスト方針` に書かれた2ケース(両方指定/両方省略)を過不足なくカバーしている。
- 参考(指摘ではなく観察): 「計画日のみ」「期限日のみ」の片方だけ指定するケースのテストは無いが、承認済みのテスト方針の範囲外のため今回は追加不要と判断。将来テストを厚くする際の候補として記録のみ残す。
- **指摘なし**(重大な問題は見つからなかった)。

## ステータス: レビュー合格(2026-09-13)
