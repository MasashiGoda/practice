# 0002: 完了済みTODOの折りたたみセクション化

## 依頼内容

完了済みのTODOは画面下部に「完了済み」としてまとめて表示したい。そのリストをクリックすると
詳細な中身(タイトル・日付など)が見えるようにする。

## 現状把握

- `app.py` の `index()`: `SELECT * FROM todos ORDER BY done ASC, id DESC` で1つのリストとして
  未完了→完了済みの順に取得し、`templates/index.html` の単一の `<ul class="todo-list">` に
  すべて描画している。完了済みタスクも常に全文(タイトル・日付)が表示された状態。
- `templates/index.html`: `<li>` の構造は「トグルボタン」「`.content`(タイトル+日付)」「削除ボタン」。
  完了済み(`li.done`)は打ち消し線とミュートカラーが `static/style.css` で適用されるのみで、
  未完了と同じ形でリストに並んでいる。
- `static/style.css`: `.todo-list` がカード状の角丸コンテナ。`li.done .title` に打ち消し線。
- `tests/test_todos.py`: 一覧表示・追加・完了切替・削除・日付表示の基本テストのみ。

## 実装方針

1. **画面構成の変更**(`templates/index.html`)
   - `todos` を Jinja の `rejectattr('done')` / `selectattr('done')` で「未完了リスト」「完了済みリスト」に分割する(DBスキーマ・SQLクエリの変更は不要)。
   - `<li>` の描画をJinjaマクロ(`{% macro render_todo(todo) %}`)として1箇所にまとめ、未完了リスト・完了済みリストの両方から呼び出す(現状の `<li>` の中身をそのまま流用、重複を避けるため)。
   - 未完了リストは既存通り `<ul class="todo-list">` としてそのまま表示する。
   - 完了済みリストが1件以上ある場合のみ、画面下部(未完了リストの後)に `<details class="completed-section">` を追加する。
     - `<summary>完了済み ({{ completed件数 }}件)</summary>` を見出しとして表示する。
     - `<details>` はデフォルトで折りたたまれた状態(HTML標準の挙動)。クリック(`<summary>` タップ)で展開すると、中に完了済みタスクの `<ul class="todo-list">` が現れる(タイトル・日付など、未完了のタスクと同じ情報量)。
     - 完了済みが0件の場合は `<details>` 自体を描画しない(空の折りたたみを出さない)。
   - 「タスクはまだありません」の空状態メッセージは、未完了・完了済みの両方が0件のときのみ表示する(全部完了済みの場合はこのメッセージを出さない)。

2. **スタイル調整**(`static/style.css`)
   - `.completed-section` に上部余白を追加し、未完了リストとの区切りをつける。
   - `.completed-section summary` は既存の `--muted` カラー・フォントサイズで、クリック可能であることが分かるスタイル(`cursor: pointer`)にする。ブラウザ標準の開閉三角マーカーはそのまま活かす(独自アイコンは作らない)。
   - 完了済みリスト内の `<ul>` は既存の `.todo-list` スタイルを流用する。

3. **`app.py` の変更なし**: データモデル・ルーティングは変更しない。表示の並び替え・分割はテンプレート側(Jinjaフィルタ)のみで完結させる。

## スコープ外

- 完了日時の記録・それによるソート(現状 `completed_at` のような列がないため、完了済み内の並び順は既存の `id` 降順のまま)。
- 完了済みセクションの開閉状態を保存する機能(ページ再読み込みで常に閉じた状態に戻る、標準の `<details>` の挙動のまま)。
- 個々の完了済みタスクをさらにクリックして追加情報を出す機能(現状タイトル・日付以外に隠すべき情報がないため、「クリックで詳細」は完了済みセクション全体の開閉として実装する)。
- 完了済みタスクの一括削除・アーカイブ機能。

## テスト方針(TDD: `/implement` の中でRed→Greenを回す)

- 完了済みタスクが1件以上あるとき、`<details class="completed-section">` と `<summary>完了済み (N件)</summary>` が表示され、その中に完了済みタスクのタイトルが含まれること。
- 完了済みタスクが0件のとき、`completed-section` が描画されないこと。
- 未完了と完了済みが混在するとき、未完了タスクは通常の `<ul class="todo-list">` に、完了済みタスクは `completed-section` の中だけに現れること(重複表示されない)。
- 全タスクが完了済みのとき、「タスクはまだありません」が表示されないこと。
- 既存テスト(一覧・追加・トグル・削除・日付表示)がすべて引き続き通ること。

## 実装メモ

- 変更ファイル: `templates/index.html`, `static/style.css`, `tests/test_todos.py`
- `templates/index.html`: `<li>` の描画を `{% macro render_todo(todo) %}` として1箇所にまとめ、
  未完了リスト・完了済みリストの両方から呼び出す形にして重複を回避。
  `todos | rejectattr('done') | list` / `todos | selectattr('done') | list` で分割(SQL・スキーマは無変更)。
  完了済みが1件以上のときのみ `<details class="completed-section"><summary>完了済み (N件)</summary>...</details>` を描画。
  空状態(「タスクはまだありません」)は未完了・完了済みの両方が0件のときのみ表示するよう分岐を追加。
- `static/style.css`: `.completed-section` / `summary` のスタイルを追加(既存の `--muted` トーンを踏襲)。
- TDDサイクルの実施メモ: 1ユニット目(完了済みセクションの表示)はRed→Greenで実装。以降の3ユニット
  (完了0件で非表示/混在時の重複なし分割/全完了時に空メッセージを出さない)は、1ユニット目の実装
  (`{% if completed %}` ガードと `rejectattr`/`selectattr` による分割)が副次的に満たしていたため、
  テスト追加時点で最初からGreenだった。実装漏れがないことをテストで確認した上で記録している。

## テスト結果

- 実行コマンド: `PYTHONPATH=./vendor python3 -m pytest tests/ -q`(生ログ: `reports/0002-pytest.txt`)
- 追加テスト(`tests/test_todos.py`):
  - `test_completed_todo_appears_in_collapsible_section`
  - `test_no_completed_section_when_nothing_done`
  - `test_active_and_completed_lists_split_without_duplication`
  - `test_all_done_does_not_show_empty_message`
- 結果: 既存7件 + 新規4件 = **11 passed**

## セキュリティチェック

- 実行コマンド: `PYTHONPATH=./vendor python3 -m bandit -r . -x ./vendor,./tests -ll -ii -f txt`(生ログ: `reports/0002-bandit.txt`)
- 結果: **No issues identified.**(Medium以上の重要度・確信度の指摘なし。既存の `# nosec B201` 以外の抑制は追加していない)

## ステータス: テスト合格(2026-09-13)
