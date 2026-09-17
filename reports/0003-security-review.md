# セキュリティレビュー(LLM) — タスク0003

対象: `git diff master...feature/0003-user-accounts`

## 手法

1. サブエージェントで `app.py`(認証・権限デコレータ、ログイン、`admin/users` 一覧・作成・削除、
   既存TODOルートのuser_idスコープ化)、`templates/login.html`・`templates/admin_users.html`・
   `templates/index.html`(ヘッダー追加分)、`static/style.css`、`tests/conftest.py` を通読し、
   下記の観点を重点的に追跡:
   - `login_required`/`admin_required` デコレータのバイパス経路の有無
   - `create_user` が非管理者から到達可能か、管理者を新規作成できてしまう昇格経路がないか
   - `delete_user` の管理者削除ガードのバイパス有無
   - `/`, `POST /todos`, `toggle`, `delete` の `user_id` スコープ漏れ(IDOR)の有無
   - ログイン時の `session.clear()` → `session["user_id"]` 設定順序(セッション固定化対策)
   - テンプレートでの `|safe`/`Markup`/`autoescape false` 等によるXSS導入の有無
   - タイミングサイドチャネル対策(ダミーハッシュ比較)の実装が正しいか
2. 見つかった指摘それぞれに対して並列サブエージェントで偽陽性フィルタリングを実施する予定だったが、
   今回は指摘0件のため実施なし。
3. 信頼度8未満の指摘は除外(今回は指摘0件のため該当なし)。

## 結果

**No qualifying vulnerabilities found.**

- `g.user` はFlaskの署名付きセッション(`session["user_id"]`)からのみ設定され、`app.secret_key`
  なしに偽造できないため、`login_required`/`admin_required` のバイパス経路は見つからなかった。
- `create_user` は `@admin_required` 配下にのみ存在し、作成するユーザーは常に `is_admin = 0` を
  ハードコードしているため、このルート経由での権限昇格経路はない。
- `delete_user` の `if target is not None and not target["is_admin"]:` ガードは管理者(id=1の
  `admin` を含む)の削除を確実にブロックしている(`test_admin_cannot_delete_the_admin_account` で
  確認済み)。
- `/`, `POST /todos`, `toggle`, `delete` の4ルートすべてでパラメータ化された `user_id = ?` 条件が
  一貫して付与されており、スコープ漏れによるIDORは見つからなかった。
- ログイン成功時は `session.clear()` の後に `session["user_id"]` を設定しており、セッション固定化を
  防ぐ順序になっている。
- 変更後のテンプレート(`login.html`, `admin_users.html`, `index.html` の追加分)に `|safe` や
  `Markup`、`{% autoescape false %}` は無く、`user.username`・`todo.title` 等はJinja2の
  デフォルトの自動エスケープのままレンダリングされているため、新規のXSS経路は見つからなかった。
- ログインのタイミングサイドチャネル対策(ユーザーが存在しない場合に `_DUMMY_PASSWORD_HASH` で
  `check_password_hash` を実行する実装)は正しく組み込まれており、存在確認とパスワード誤りの
  処理時間の差が縮小されている。

## 参考: 既知の受容済みトレードオフ(今回のスコープ内での新規指摘ではない)

- デフォルト管理者アカウント `admin`/`admin` は、`tasks/0003-user-accounts.md` の計画段階で
  ユーザー自身が明示的に指示した初期値であり、承認済み・`bandit` でも `# nosec B106` の理由付きで
  対応済み。本番運用を想定しないローカル練習用アプリという前提での受容済みリスクであり、
  このレビューでの新規指摘としては扱わない。
- CSRF対策なし・パスワード複雑さ要件なし・レート制限なしは、いずれもタスク計画の「スコープ外」に
  明記された既知の設計判断であり、今回の指摘対象外とする。
