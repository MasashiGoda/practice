---
description: レビュー合格後、確認を挟んでPRを作成しmasterへマージする(ステップ4/4: マージ)
argument-hint: <id>
---

あなたはこのプロジェクト(CLAUDE.md参照)の開発フロー、ステップ4「マージ」を実行する。
マージはPRベースで行う(ローカルで直接 `master` にマージしない)。

引数: $ARGUMENTS (タスクID)

## 手順

1. `tasks/<id>-*.md` を読み、ステータスが「レビュー合格」であることを確認する。そうでなければ処理を止め、必要なステップを案内する。
2. マージ内容の要約(変更ファイル、テスト結果、レビュー結論)をユーザーに提示し、**必ず**「`feature/<id>-<slug>` を push してPRを作成してよいですか?」と明示的に確認する。承認が得られるまでpush・PR作成を実行しない。
3. 承認後:
   - `git push -u origin feature/<id>-<slug>`
   - `gh pr create` でPRを作成する(base: `master`、タイトルは課題タイトル、本文に変更概要・テスト結果・レビュー結論を記載)。`gh` が使えない環境の場合は、GitHubの比較URL(`https://github.com/<owner>/<repo>/compare/master...feature/<id>-<slug>?expand=1`)を案内し、ユーザー自身にPR作成を依頼する。
4. PRのマージは、ユーザーがGitHub上で行うか、ユーザーから明示的に指示があった場合のみ `gh pr merge` で実行する(無断でマージしない)。
5. マージ確認後:
   - `git fetch origin` してから `git checkout master && git pull origin master` でローカルを最新化する。
     `.claude/commands/` 等はBashのサンドボックスから書き込めないため、`git checkout`/`pull` がこれらのファイルの unlink で失敗することがある。その場合は `git reset origin/master`(indexとHEADのみ移動、作業ツリーは変更しない)で対処し、`.claude/commands/` 以外の変更ファイルを `git checkout HEAD -- <対象ファイル…>` で個別に復元する。
   - 念のため `PYTHONPATH=./vendor python3 -m pytest tests/ -q` を実行し、通ることを確認する
6. タスクファイルのステータスを「マージ済み」に更新し、PR番号・マージコミットのハッシュを記録する。`tasks/INDEX.md` も更新する。
7. フィーチャーブランチ(ローカル・リモート)を削除してよいかユーザーに確認し、了承されれば削除する。
