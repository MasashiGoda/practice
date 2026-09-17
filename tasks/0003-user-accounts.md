# 0003: ログイン機能とユーザー作成・削除機能の追加

## 依頼内容

- ログイン機能を追加する。
- ユーザー作成・削除機能を追加する。登録可能な一般ユーザー数は最大10人まで(この上限に管理者
  `admin` は含めない。つまり `admin` 1人 + 一般ユーザー最大10人 = 最大11アカウント)。
- ユーザーごとに別々のTODOリストを持てるようにする(あるユーザーが作成したTODOは他のユーザーには
  見えない)。
- 管理者権限を追加する。デフォルトで `admin` というユーザーが管理者となり、パスワードは `admin`。
- **(今回の指示変更)** ユーザーの**作成・削除ともに管理者のみが行える**。一般ユーザーによる
  自己登録(セルフサインアップ)は廃止する。一般ユーザーは、管理者が発行したユーザー名・パスワードで
  ログインするのみで、アカウントの作成・削除には一切関与しない。

**解釈の確認**:
- 「ユーザーごとに別のtodoリストを作れます」は、1ユーザーが複数の名前付きリストを持てる機能ではなく、
  「ユーザーAのTODOとユーザーBのTODOが分離されている(データが混ざらない)」という意味として実装する。
- 登録可能数「最大10人」は一般ユーザー(`is_admin = 0`)のみのカウントとし、`admin` は含めない
  (今回の指示どおり)。

## 現状把握

- `app.py`: Flask + SQLite。認証機構なし。`todos` テーブルは `id`, `title`, `done`, `created_at`,
  `planned_date`, `due_date` のみで、ユーザーの概念が存在しない。
- ルートは `/`(一覧)、`POST /todos`(作成)、`POST /todos/<id>/toggle`(完了切替)、
  `POST /todos/<id>/delete`(削除)の4つ。いずれも認証チェックなし、全件が単一の共有リストとして扱われる。
- `get_db()` / `close_db()` は `g` を使ったリクエストスコープの単一DB接続。`init_db()` は
  `CREATE TABLE IF NOT EXISTS` のみで、既存テーブルへの列追加(マイグレーション)は行っていない
  (タスク0001の前例と同様、開発用 `todo.db` は作り直す前提)。
- `vendor/` に `werkzeug`(Flaskの依存として)が既に導入済みで、`werkzeug.security.generate_password_hash` /
  `check_password_hash` がそのまま使える(scryptベース、追加インストール不要)ことを確認済み。
- `templates/index.html`: 追加フォーム・TODO一覧(未完了/完了済み折りたたみ)のみ。ヘッダーやログイン状態の
  表示は存在しない。
- `static/style.css`: `:root` にライト/ダーク両対応のカラー変数あり。フォーム・リストのスタイルは
  既存クラス(`.add-form`, `.todo-list`, `.dates` 等)で完結している。
- `tests/conftest.py`: `client` フィクスチャが一時DBファイルを作って `init_db()` を呼び、
  `app.test_client()` を返す。認証状態という概念がないため、現状は「誰でも触れる」前提でテストしている。
- `tests/test_todos.py`: 一覧・作成・完了切替・削除・日付表示・完了済みセクションのテストが14件ある。
  いずれもログイン不要な前提で書かれている。
- セッション機構(`app.secret_key` 相当)は未設定。ログイン機能にはFlaskの署名付きセッションが必要。

## 実装方針

### 1. データモデル変更 (`app.py`)

- `users` テーブルを新設:
  ```sql
  CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      username TEXT NOT NULL UNIQUE,
      password_hash TEXT NOT NULL,
      is_admin INTEGER NOT NULL DEFAULT 0,
      created_at TEXT NOT NULL DEFAULT (datetime('now'))
  )
  ```
- `todos` テーブルに `user_id INTEGER NOT NULL` を追加(既存カラムはそのまま):
  ```sql
  CREATE TABLE IF NOT EXISTS todos (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL,
      title TEXT NOT NULL,
      done INTEGER NOT NULL DEFAULT 0,
      created_at TEXT NOT NULL DEFAULT (datetime('now')),
      planned_date TEXT,
      due_date TEXT
  )
  ```
  外部キー制約(`REFERENCES users(id)`)は付けるが、SQLiteはデフォルトで `PRAGMA foreign_keys` が
  無効なため実効的なカスケード削除には頼らず、ユーザー削除時に `app.py` 側で明示的に
  「そのユーザーのtodoを削除 → ユーザー行を削除」を行う。
- `init_db()` の中で、ユーザー名 `admin` が未登録なら、デフォルト管理者をシードする:
  ユーザー名 `admin` / パスワード `admin`(`generate_password_hash("admin")`)/ `is_admin = 1`。
  既に存在する場合は何もしない(冪等)。
  - パスワード `admin` は明示的な指示による初期値であり、極めて推測されやすい。本番運用は想定しない
    練習用ローカルアプリという前提(既存の `debug=True` の `# nosec` と同じ考え方)で受け入れる。
    パスワード変更機能自体は今回のスコープ外。
- 実装時に既存の開発用 `todo.db` を削除して新スキーマで作り直す(タスク0001と同じ方針。中身は
  練習用データなので破棄してよい)。
- `app.secret_key` を追加(`app.config.setdefault("SECRET_KEY", secrets.token_hex(32))`)。
  プロセス起動ごとにランダム生成する方式にする。サーバー再起動でセッションが切れる(再ログインが
  必要になる)が、ローカル練習用アプリでは許容範囲と判断する。

### 2. 認証・ユーザー管理ロジック (`app.py`)

- `login_required` デコレータ: `session.get("user_id")` が無ければ `/login` へリダイレクト。
- `admin_required` デコレータ: `login_required` に加えて `g.user["is_admin"]` が真でなければ
  403(または `/` へリダイレクト+エラーメッセージ)。
- `@app.before_request` で `g.user`(現在ログイン中のユーザー行、未ログインなら `None`)をセットし、
  テンプレート側でユーザー名表示・管理者判定に使う。
- 新規ルート:
  - `GET/POST /login`: ログイン(一般ユーザー・管理者共通)。
    - `check_password_hash` で照合。失敗時は「ユーザー名またはパスワードが正しくありません」という
      共通のエラーメッセージ(ユーザー名の存在有無を推測されないようにするため、失敗理由を分けない)。
    - 成功時: `session["user_id"]` をセットして `/` にリダイレクト。
    - 自己登録ページへのリンクは置かない(セルフサインアップ廃止のため)。
  - `POST /logout`: `session.clear()` して `/login` にリダイレクト。
  - `GET /admin/users`(**管理者のみ**): ユーザー作成フォーム + 登録済み全ユーザーの一覧
    (ユーザー名・管理者かどうか・作成日時)を1ページで表示。各行(管理者以外)に削除ボタンを置く。
  - `POST /admin/users`(**管理者のみ**): 新規の一般ユーザーを作成する。
    - バリデーション: ユーザー名・パスワードが空でないこと(パスワードは4文字以上)。
    - ユーザー名が既に使われている場合(`admin` 含む)はエラー表示。
    - 一般ユーザー(`is_admin = 0`)の人数が既に10人に達している場合はエラーメッセージ
      (「登録できる一般ユーザー数の上限(10人)に達しています」)を表示し、作成を拒否
      (`admin` はこのカウントに含めない)。
    - 作成されるユーザーは常に `is_admin = 0`(このフォームから管理者は作れない)。
    - 成功時は `/admin/users` に戻り、作成したユーザーが一覧に表示される(作成しても管理者自身の
      セッションは変わらない。新規ユーザーは別途 `/login` でログインする)。
  - `POST /admin/users/<id>/delete`(**管理者のみ**): 対象ユーザーに紐づく `todos` を削除 →
    `users` から対象行を削除。**対象が管理者(`is_admin = 1`)の場合は拒否する**(自分自身を含め、
    管理者アカウントは削除できないようにする。管理者を昇格させる機能が無い設計なので、誤って唯一の
    管理者を消してロックアウトする事故を防ぐガード)。
- 既存の `/`, `POST /todos`, `POST /todos/<id>/toggle`, `POST /todos/<id>/delete` に
  `@login_required` を付与し、それぞれ `user_id = ?` 条件をSQLに追加してログイン中のユーザーの
  行だけを対象にする(一覧取得・作成・完了切替・削除のすべてで自分のtodoにしか触れないようにする。
  他人のtodo IDを推測して叩いても対象がヒットせず何も起きない、というIDOR対策込み)。これは管理者で
  あっても例外なく「自分のtodoリストのみ」を操作する(管理者に他人のTODO閲覧権限は与えない。
  「スコープ外」参照)。

### 3. UI変更 (`templates/`, `static/style.css`)

- 新規 `templates/login.html`: ユーザー名・パスワード入力フォーム、エラーメッセージ表示欄のみ
  (登録ページへのリンクは無し)。
- 新規 `templates/admin_users.html`:
  - 上部にユーザー作成フォーム(ユーザー名・パスワード入力、送信ボタン)。エラーメッセージ表示欄。
  - 下部にユーザー一覧テーブル(ユーザー名/管理者バッジ/作成日時/削除ボタン)。管理者行には
    削除ボタンを出さない(サーバー側ガードに加えてUI側でも出さない、二重の防御)。削除ボタンには
    `onclick="return confirm('このユーザーを削除します。よろしいですか？')"` を付ける。
- `templates/index.html` にヘッダー(`.topbar` 等)を追加:
  - ログイン中のユーザー名を表示。
  - 「ログアウト」ボタン(`POST /logout`)。
  - ログイン中のユーザーが管理者の場合のみ「ユーザー管理」リンク(`GET /admin/users`)を表示。
- `static/style.css` に `.topbar` 用のスタイル、`login.html`/`admin_users.html` 用のシンプルな
  フォーム・テーブルスタイル(既存の `.add-form input` 等のトーン&マナーに合わせる)、エラーメッセージ用の
  スタイル(例: `.flash-error`)、管理者バッジ用のスタイルを追加。
- `templates/register.html` は作らない(セルフサインアップ廃止のため)。
- UI変更があるため、`/dev-review` で自動的にデザイン監査が行われる。

### 4. テスト用フィクスチャの変更 (`tests/conftest.py`)

- 一時DB作成 + `init_db()` 呼び出しを共通化(`admin` が自動シードされる状態になる)。
- 新しい `raw_client` フィクスチャ: 未ログイン状態の `test_client()` をそのまま返す
  (認証・管理者系のテスト用)。
- 新しい `admin_client` フィクスチャ: 独立した `test_client()` でデフォルト管理者
  (`admin` / `admin`)にログイン済みの状態を返す(管理者機能のテスト用)。
- 既存の `client` フィクスチャ: `admin_client` で `POST /admin/users` によりテスト用の一般ユーザー
  (例: `testuser` / `testpass123`)を1人作成した後、**別の** `test_client()` インスタンスでそのユーザーに
  ログインした状態を返す(既存の14件のテストが無修正で動き続けるようにするため。管理者用クッキーと
  一般ユーザー用クッキーを混ぜないよう、クライアントインスタンスを分ける)。

## スコープ外

- 1人のユーザーが複数の名前付きTODOリストを切り替えて持てる機能。
- 一般ユーザーによる自己登録(セルフサインアップ)。今回の指示により廃止、ユーザー作成は管理者のみ。
- 一般ユーザーによる自分自身のアカウント削除。削除は管理者のみ。
- 管理者が他ユーザーのTODOを閲覧・操作できる機能(管理者もユーザー管理のみで、TODOは自分のリストだけ)。
- 一般ユーザーを管理者に昇格させる機能・管理者を追加作成する機能(管理者は `admin` の1人のみ)。
- 管理者アカウントのパスワード変更機能・初回ログイン時の強制パスワード変更。
- 管理者がユーザー作成時に発行した初期パスワードを本人に安全に伝える仕組み(メール送信等)。
  今回はローカル練習用のため、管理者が口頭・別チャネルで伝える運用を前提とする。
- パスワードリセット・メール認証・二段階認証。
- パスワードの複雑さ要件(記号必須など)。ユーザー名の変更機能。
- ログイン試行回数の制限・レート制限。
- CSRF対策トークンの導入。既存アプリの他のフォーム(TODOの作成・完了切替・削除)も同様に
  CSRF対策なしで運用されており、今回もその前提を踏襲する(ローカル練習用・単一ユーザーが
  自分のブラウザで使うことを想定した既存方針に合わせる)。`security-review` スキルで
  指摘された場合は、既知の許容済みリスクとして扱う。
- 既存の `todo.db` のデータ移行(前例どおり削除して作り直す)。

## テスト方針

TDD(Red→Green)で、以下の単位ごとに「失敗するテストを先に書く→実装→Green確認」を繰り返す。

1. `tests/conftest.py` の `raw_client` / `admin_client`(デフォルト管理者ログイン済み) /
   `client`(admin経由で作成された一般ユーザーでログイン済み)フィクスチャへの変更。
2. `init_db()` 実行後、`admin` ユーザーが `is_admin=1` で存在し、パスワード `admin` でログイン
   できること。
3. ログイン: 正しい認証情報で成功しセッションが張られること。誤ったパスワード・存在しないユーザー名で
   エラーになること。
4. 未ログイン状態で `/`、`POST /todos`、`POST /todos/<id>/toggle`、`POST /todos/<id>/delete`、
   `GET /admin/users`、`POST /admin/users`、`POST /admin/users/<id>/delete` にアクセスすると
   `/login` にリダイレクトされること。
5. 管理者権限によるユーザー作成: 一般ユーザーが `POST /admin/users`(および `GET /admin/users`)に
   アクセスすると拒否されること(管理者以外は作成できない)。
6. 管理者権限によるユーザー作成: 管理者が `POST /admin/users` で一般ユーザーを作成でき、
   作成されたユーザーは `is_admin=0` で、そのユーザー名・パスワードで `/login` できること。
7. 管理者権限によるユーザー作成: ユーザー名重複時(`admin` を含む)にエラー表示・作成されないこと。
8. 管理者権限によるユーザー作成: 一般ユーザーが既に10人作成済みの状態で11人目の作成がエラーになり、
   作成されないこと(`admin` はこの10人のカウントに含めない)。
9. ログアウト: セッションが破棄され、以降は保護ページに再度ログインが必要になること。
10. マルチユーザー分離: 管理者が作成したユーザーAのTODOがユーザーBの一覧に出ないこと。ユーザーBが
    ユーザーAのtodo IDに対して `toggle`/`delete` を実行しても対象が変化しないこと(IDOR対策の確認)。
11. 管理者権限によるユーザー削除: 一般ユーザーが `POST /admin/users/<id>/delete` にアクセスすると
    拒否されること。
12. 管理者権限によるユーザー削除: 管理者が一般ユーザーを削除でき、そのユーザーのtodoも一緒に
    削除されること。削除後は同じユーザー名で再度作成できること(枠が空くこと)。
13. 管理者権限によるユーザー削除: 管理者が `admin` 自身(または任意の `is_admin=1` ユーザー)を
    削除しようとすると拒否され、`admin` ユーザーは削除されずに残ること。

既存の `tests/test_todos.py`(14件)は無修正のまま green を維持することを確認する。
最後に `bandit` によるセキュリティチェックも行う(パスワードハッシュ化・セッション周りは
`werkzeug`/Flask標準機能に任せているため、`bandit` 上の新規指摘は出ない見込みだが確認する)。

## 実装メモ

- 変更したファイル:
  - `app.py`: `users` テーブル追加(`is_admin` 列込み)、`init_db()` での `admin`/`admin` 自動シード、
    `app.secret_key`(プロセス起動時にランダム生成)、`login_required`/`admin_required` デコレータ、
    `/login`・`/logout`・`GET/POST /admin/users`・`POST /admin/users/<id>/delete` を新設。
    既存の `/`, `POST /todos`, `toggle`, `delete` は `@login_required` を付与し、SQLに
    `user_id = ?` 条件を追加(IDOR対策込み)。
  - `templates/login.html`(新規)、`templates/admin_users.html`(新規、ユーザー作成フォーム+一覧+
    管理者行には削除ボタン非表示)、`templates/index.html`(ヘッダーにユーザー名・ログアウト・
    管理者のみ「ユーザー管理」リンクを追加)。
  - `static/style.css`: `.topbar`, `.auth-main`/`.auth-form`, `.flash-error`, `.user-table`,
    `.admin-badge` を追加。
  - `tests/conftest.py`: `_configured_app`(共通の一時DBセットアップ)、`raw_client`(未ログイン)、
    `admin_client`(デフォルト管理者ログイン済み)、`client`(admin経由で作成した一般ユーザー
    `testuser`でログイン済み)の4フィクスチャに再構成。
  - `tests/test_auth.py`, `tests/test_admin_users.py`, `tests/test_multi_user_todos.py`(新規)。
- 実装上の判断:
  - ユーザー削除時は `PRAGMA foreign_keys` に頼らず、`app.py` 側で明示的に
    `DELETE FROM todos WHERE user_id = ?` → `DELETE FROM users WHERE id = ?` の順で実行(計画どおり)。
  - 一般ユーザー数の上限判定は `SELECT COUNT(*) FROM users WHERE is_admin = 0` とし、`admin` を
    含めない(計画で確定した解釈どおり)。
  - `admin_required` は非管理者に対して `403 Forbidden`(プレーンテキスト)を返す方針とした
    (計画では「403または適切なリダイレクト」としていたが、管理者専用ページへの誤操作を明確に
    伝える意味で403を採用)。
  - テストフィクスチャは `with app.test_client() as client:` を使わず、素の `test_client()` を返す
    形に変更した。理由: `with` はレスポンス後もリクエストコンテキストを保持する仕様のため、
    同一テスト内で複数のクライアント(admin用・一般ユーザー用)を交互に操作すると
    Flaskのコンテキストスタックが壊れる(`AssertionError: Popped wrong request context`)ことが
    実装中に判明したため。今回のテストでは操作後のテンプレートコンテキスト確認は不要なので、
    素の `test_client()` で問題ない。
  - マルチユーザー分離のIDOR対策(`toggle`/`delete` のSQLから `AND user_id = ?` を一時的に外す)を
    手動で検証し、`tests/test_multi_user_todos.py` がその欠陥を確実に検知することを確認した
    (その後すぐ元に戻した)。

## テスト結果

- `PYTHONPATH=./vendor python3 -m pytest tests/ -q` → **27 passed**(既存の `tests/test_todos.py`
  11件は無修正のまま green、新規16件を追加: `test_auth.py` 6件、`test_admin_users.py` 8件、
  `test_multi_user_todos.py` 2件)。
- 生ログ: [reports/0003-pytest.txt](../reports/0003-pytest.txt)
- 追加したテストの要約:
  - ログイン成功・失敗(誤パスワード/未知のユーザー名)、ログアウト、未ログイン時の各保護ルートへの
    リダイレクト。
  - 管理者以外による `GET/POST /admin/users`・`POST /admin/users/<id>/delete` の拒否(403)。
  - 管理者によるユーザー作成(成功・重複ユーザー名・`admin`との重複・一般ユーザー10人到達での拒否)。
  - 管理者によるユーザー削除(削除成功・紐づくtodoの削除・枠の再利用・`admin`自身の削除拒否)。
  - マルチユーザー分離(他ユーザーのtodoが見えないこと、他ユーザーのtodo IDに対する
    toggle/deleteが効かないこと)。

## セキュリティチェック

- `PYTHONPATH=./vendor python3 -m bandit -r . -x ./vendor,./tests -ll -ii -f txt` →
  **No issues identified.**(Medium以上の指摘はゼロ)
- 生ログ: [reports/0003-bandit.txt](../reports/0003-bandit.txt)
- `# nosec` で明示的に許容した箇所: `app.py` の `init_db()` 内、デフォルト管理者のパスワード
  リテラル `"admin"` に対して `# nosec B106 -- 練習用ローカルアプリの初期管理者パスワード。
  ユーザー指示による固定値`。理由: ユーザーからの明示的な指示で `admin`/`admin` を初期値とする
  ことが決まっており、本番運用を想定しないローカル練習用アプリという前提(既存の `debug=True` の
  `# nosec` と同じ考え方)で受け入れる。Bandit上はLow重要度・Medium確信度の指摘であり、
  「Medium以上は修正必須」という基準には該当しないが、意図的な選択であることを明示するために
  `nosec` コメントを付けている。

## デザイン監査

`templates/`(`login.html`, `admin_users.html`, `index.html`)・`static/style.css` に変更があるため実施。

- 自己レビューで以下を確認・修正した:
  - `.topbar` に `flex-wrap: wrap` を追加し、ユーザー名が長い場合や狭い画面幅でもヘッダーの
    要素(ユーザー名・ナビ・ログアウト)が折り返して重ならないようにした。
  - `.topbar .username` と `.user-table th/td` に `overflow-wrap: anywhere` を追加し、長い
    ユーザー名が原因でレイアウトが崩れないようにした。
  - `admin_users.html` のユーザー一覧テーブルを `.user-table-wrapper`(`overflow-x: auto`)で
    包み、モバイル幅(~400px)で列が多い場合でもページ全体が横スクロールせず、テーブル内だけ
    スクロールできるようにした。
  - ライト/ダーク配色は既存の `:root` カラー変数(`--card`, `--border`, `--muted`, `--accent` 等)
    をそのまま再利用しており、新規のハードコード色は `.flash-error`(`#ef4444`)と
    `.delete-btn:hover` 相当のみ(いずれも既存の削除ボタンの配色 `#ef4444` を踏襲、新規追加ではない)。
  - フォーカス状態は独自に `outline: none`等を指定していないため、ブラウザ標準のフォーカスリングが
    ボタン・リンク・入力欄すべてで有効なまま。
  - タップ領域は既存の `.toggle-btn`/`.delete-btn` と同等のサイズ感(`.logout-form button`,
    `.delete-btn`)で統一しており、新規追加ぶんだけ極端に小さい・大きいという不整合はない。
  - 日本語の文言(ボタンラベル・確認ダイアログ・エラーメッセージ)はいずれも短い一文で、
    禁則処理が問題になるような改行を挟む長さではない。
- サンドボックスからブラウザ確認ができないため、実機確認をユーザーに1回依頼した(下記「ユーザー確認」参照)。

**ユーザー確認**: `PYTHONPATH=./vendor python3 app.py` で実機確認を実施。ログイン、ユーザー管理
(作成・削除ボタンの表示制御)、マルチユーザーでのTODO分離、モバイル幅、ダークモードの各観点で
問題なし(承認: 2026-09-17)。

## レビュー

### コードレビュー

- 実装は承認済みの `## 実装方針` に沿っており、`## スコープ外` に書かれた機能(自己登録、
  自己アカウント削除、他ユーザーTODOの閲覧、管理者昇格、パスワード変更等)には手を出していない。
- レビュー中に見つけて自分で修正した2点:
  1. **ログインのタイミングサイドチャネル**: 修正前は、ユーザー名が存在しない場合に
     `check_password_hash` を呼ばずに即エラーにしていたため、「ユーザーが存在する場合(ハッシュ比較
     あり)」と「存在しない場合(ハッシュ比較なし)」で応答時間に差が出て、ユーザー名の存在を
     タイミングから推測できる余地があった。`_DUMMY_PASSWORD_HASH` を用意し、ユーザーが存在しない
     場合もダミーハッシュに対して必ず `check_password_hash` を実行するように修正し、既存判定と
     未知ユーザー名判定で同じ処理コストがかかるようにした。
  2. **重複コードの整理**: `admin_users()` と `create_user()` のエラー再表示パスで、ユーザー一覧を
     取得する同じSQLが2箇所にあったため、`_all_users(db)` ヘルパーに切り出した。
- テストは実装前に失敗を確認してから実装する手順(Red→Green)で追加しており、形だけのテストに
  なっていないことを、IDOR対策のSQL条件を一時的に外して `tests/test_multi_user_todos.py` が
  実際に検知することを確認する形で検証済み(「実装メモ」参照)。
- `## セキュリティチェック` に記載の `bandit` 結果は `No issues identified.`(レビュー中の修正後も
  再実行して確認済み、`reports/0003-bandit.txt` を更新済み)。`# nosec B106` はデフォルト管理者
  パスワードという、ユーザー自身が明示的に指示した既知のトレードオフに対する妥当な抑制であり、
  単なる指摘逃れではない。
- 指摘なし(上記2点は指摘と同時に自分で修正済みのため、修正後の状態としては指摘なし)。

## セキュリティレビュー(LLM)

`security-review` スキルで `feature/0003-user-accounts` の差分をレビュー。認証・認可バイパス、
権限昇格、IDOR、セッション固定化、テンプレートでのXSS導入、タイミングサイドチャネルを重点的に
確認したが、**指摘なし**(No qualifying vulnerabilities found)。

デフォルト管理者パスワード `admin`/`admin`・CSRF対策なし・レート制限なしは、タスク計画段階で
ユーザーが明示的に指示・承認済みのトレードオフであり、`bandit` でも対応済みのため、今回の
LLMレビューでは新規指摘として扱っていない。

生ログ: [reports/0003-security-review.md](../reports/0003-security-review.md)

## ステータス: マージ済み(PR #3, マージコミット 4e926d5)
