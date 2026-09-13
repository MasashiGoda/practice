# practice — Flask TODOアプリ

練習用のローカルTODOアプリ。Flask + SQLite、サーバーサイドレンダリング。

## セットアップと実行

依存関係はこのサンドボックス環境では `~/.local` が書き込み不可・`venv` も使えなかったため、
プロジェクト内 `vendor/` にターゲットインストールしている(`vendor/` は `.gitignore` 対象)。

```bash
# 依存関係の追加
pip3 install --no-cache-dir --target=./vendor <パッケージ名>

# 実行 (http://127.0.0.1:5000)
PYTHONPATH=./vendor python3 app.py

# テスト
PYTHONPATH=./vendor python3 -m pytest tests/ -q

# セキュリティチェック(決定論的な静的解析)
PYTHONPATH=./vendor python3 -m bandit -r . -x ./vendor,./tests -ll -ii -f txt
```

**重要な注意点**: Claude Codeのサンドボックス化されたBashはネットワーク的に隔離されている。
ここでFlask開発サーバーを起動してもログ上は成功して見えるが、ユーザーのブラウザや
別のBash呼び出しからの `curl` では到達できない(`Connection refused` になる)。
動作確認が必要なときは、ユーザー自身の端末で起動してもらうこと
(`!` プレフィックス、または別ターミナル)。エージェント側で `curl` 等による
自動確認を試みない。

同様に、このサンドボックスにはGitHub向けの認証情報がなく `git push` は常に失敗する
(`fatal: could not read Username for 'https://github.com'`)。確認済みの制約のため、
`/merge` では最初から `push` をユーザーに `!` プレフィックスで実行してもらう(こちらで
試して失敗を報告する、という手順は踏まない)。

## 開発フロー(4ステップ・関所3箇所)

機能追加・変更は、思いつきで直接コードを書かず、必ず以下のコマンドを順番に使う。
各コマンドの詳細な手順は `.claude/commands/*.md` を参照。

1. `/dev-plan <やりたいこと>` — 課題と既存コードを読み、実装方針を `tasks/<id>-<slug>.md` に書き出し、
   その場で(会話内の返信で)承認を得る。新しいコマンドを介さず、承認・修正のやり取りはそのまま
   チャットで完結する(関所①)。
2. `/implement <id>` — `feature/<id>-<slug>` ブランチを作成し、承認された方針をTDD(Red→Green)で
   実装する。テストは後付けではなく、機能単位で「失敗するテストを先に書く→実装→Green確認」を
   繰り返しながら進める。最後に `bandit`(決定論的な静的解析)でセキュリティチェックも行う。
3. `/dev-review <id>` — 差分のコードレビューと、`security-review` スキルによるLLMベースの
   セキュリティレビューを行う。`templates/`・`static/` に変更がある場合のみ、その中でデザイン
   監査も行い、ユーザーに実機確認を1回だけ依頼する(関所②、UI変更がなければ自動で通過)。
4. `/merge <id>` — レビュー合格後、**必ず確認を挟んでから**(関所③)`feature/<id>-<slug>` を
   `origin` にpushし、`master` へのPull Requestを作成する。マージ自体もPR経由で行う
   (ローカルで直接 `master` にマージしない)。

タスクの状態は `tasks/INDEX.md`(一覧表)と `tasks/<id>-<slug>.md`(詳細)で管理する。
ステップを飛ばして実装・承認・マージをしない。各コマンドは前提ステータスを確認し、
満たしていなければ処理を止める。

旧フローにあった `/approve`・`/test`・`/design-audit` は上記4コマンドに統合され廃止済み
(呼び出すと案内が表示される)。`/dev-review` は名称を維持したまま `/design-audit` を
吸収している(組み込みコマンド `/review` との名前衝突を避けるため、統合先はこの名前にした)。

## 規約

- ブランチ名: `feature/<id>-<slug>`
- mainブランチ名: `master`
- `origin`(GitHub)は設定済み。マージはPRベースで行う: `/merge <id>` の中でレビュー合格後・確認を挟んだ上でブランチを `push` し、`master` 向けのPull Requestを作成する。それ以外のタイミングでの `push` は指示がない限り行わない。
- テストは `pytest`、TDD(Red→Green→Refactor)を基本とする
- セキュリティチェックは二段構え: `bandit`(決定論的な静的解析、`/implement` 内)と
  `security-review` スキル(LLMベース、`/dev-review` 内)。`bandit` のMedium以上の指摘は修正必須、
  意図的に許容する場合のみ `# nosec <ID> -- 理由` を付ける
- `reports/<id>-pytest.txt`・`reports/<id>-bandit.txt`・`reports/<id>-security-review.md` に
  各タスクの実行結果(生ログ)を保存し、リポジトリにコミットする(`vendor/` と異なりgitignore対象外)。
  後から任意のタスクの実行結果を参照できるようにするための記録用ディレクトリ
