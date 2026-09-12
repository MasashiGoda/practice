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
```

**重要な注意点**: Claude Codeのサンドボックス化されたBashはネットワーク的に隔離されている。
ここでFlask開発サーバーを起動してもログ上は成功して見えるが、ユーザーのブラウザや
別のBash呼び出しからの `curl` では到達できない(`Connection refused` になる)。
動作確認が必要なときは、ユーザー自身の端末で起動してもらうこと
(`!` プレフィックス、または別ターミナル)。エージェント側で `curl` 等による
自動確認を試みない。

## 開発フロー(7ステップ・承認ゲート付き)

機能追加・変更は、思いつきで直接コードを書かず、必ず以下のコマンドを順番に使う。
各コマンドの詳細な手順は `.claude/commands/*.md` を参照。

1. `/plan <やりたいこと>` — 課題と既存コードを読み、実装方針を `tasks/<id>-<slug>.md` に書き出す
2. `/approve <id>` — 方針を承認する、またはコメント付きで差し戻す(承認ゲート)
3. `/implement <id>` — `feature/<id>-<slug>` ブランチを作成し、承認された方針通りに実装する
4. `/test <id>` — 動作確認テストを書いて実行する(TDD: 可能な範囲でRed→Green)
5. `/design-audit <id>` — 画面(templates/static)に変更がある場合のみ、使い勝手・禁則を点検する
6. `/review <id>` — 差分をレビューし、結果を課題ファイルにコメントとして記録する
7. `/merge <id>` — レビュー合格後、**必ず確認を挟んでから** `master` にマージする

タスクの状態は `tasks/INDEX.md`(一覧表)と `tasks/<id>-<slug>.md`(詳細)で管理する。
ステップを飛ばして実装・承認・マージをしない。各コマンドは前提ステータスを確認し、
満たしていなければ処理を止める。

## 規約

- ブランチ名: `feature/<id>-<slug>`
- mainブランチ名: `master`
- `origin`(GitHub)は設定済みだが、指示がない限り `push` しない(この開発フローはローカルの `master` へのマージまでを扱う)
- テストは `pytest`、TDD(Red→Green→Refactor)を基本とする
