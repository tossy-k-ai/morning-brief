# news-digest セットアップ手引き（Windows）

このプロジェクトは**あなたのWindows PC上で動かす前提**です。クラウド側のClaude Code
（claude.ai/code のセッション）からは、あなたのPCのファイル・Obsidian Vault・
タスクスケジューラには手が届きません。セットアップは**ローカルのClaude Codeに任せる**のが
いちばん早いです。

---

## いちばん簡単な方法: ローカルのClaudeに丸投げする

Windows PCで:

```
git clone https://github.com/tossy-k-ai/morning-brief.git
cd morning-brief\news-digest
claude
```

`claude` が起動したら、以下をそのまま貼り付けてください。

```
news-digest のセットアップをお願いします。

1. このフォルダの README.md と SETUP.md を読んでください
2. pip install -r requirements.txt を実行してください
3. 私のObsidian Vaultの実際の場所を探して、config.yaml の obsidian.vault_path を
   書き換えてください。既存の「投資分析」フォルダがあるVaultの中に、このダイジェスト
   専用の新しいフォルダを作る想定です（既存フォルダには書き込まないこと）
4. .env.example をコピーして .env を作ってください。SLACK_WEBHOOK_URL の値は私が貼ります
5. python setup_check.py を実行して、FAILがなくなるまで直してください
6. run_daily.bat を実行して、Slackにダイジェストが届くか、Obsidianに
   YYYY-MM-DD.md ができるかを確認してください
7. 失敗したら logs\ の最新ログを読んで原因を直し、直ったら再実行してください
8. 最後に、タスクスケジューラに毎朝7:00で登録してください（SETUP.md に schtasks の
   コマンド例があります）

注意: ANTHROPIC_API_KEY は設定しないでください。Claude Proサブスクの認証で動かす
前提です。
```

ローカルのClaudeはファイルの読み書きもコマンド実行もできるので、3〜8はほぼ自動で
進みます。あなたがやるのはSlack Webhook URLを貼ることくらいです。

---

## 自分で手を動かす場合

### 1. 前提確認

```
python setup_check.py
```

以下を一度に確認します（モデルの呼び出しもSlack投稿も行わないので、何度実行しても
無料です）:

- Python 3.10以降か
- requests / feedparser / PyYAML が入っているか
- `zoneinfo` で `Asia/Tokyo` が引けるか（**Windowsは `tzdata` が無いと失敗します**）
- `claude` コマンドが見つかるか、`--version` が通るか
- `ANTHROPIC_API_KEY` が設定されて**いない**か（設定されていると従量課金APIに
  流れる恐れがあるため警告します）
- `SLACK_WEBHOOK_URL` が `.env` か環境変数にあるか
- `config.yaml` の Obsidian Vaultパスが実在し、書き込めるか
- `data/` `logs/` に書き込めるか

### 2. 配信テスト

```
run_daily.bat
```

ログは `logs\YYYY-MM-DD.log` に出ます。STEP1→2→3のどこで止まったかが分かります。

STEP3（配信）だけを試したい場合は、`data\summary.md` が残っている状態で:

```
python src\distribute.py
```

### 3. タスクスケジューラに登録（コマンド1行）

GUIを使わずに登録できます。管理者権限のコマンドプロンプトで、パスを自分の環境に
合わせて実行してください:

```
schtasks /create /tn "news-digest daily" /tr "\"C:\Users\俊宏\morning-brief\news-digest\run_daily.bat\"" /sc daily /st 07:00 /f
```

確認・手動実行・削除:

```
schtasks /query /tn "news-digest daily"
schtasks /run   /tn "news-digest daily"
schtasks /delete /tn "news-digest daily" /f
```

---

## ⚠️ PCの電源についての注意

GitHub Actions版（リポジトリ直下の `morning-brief` 本体）と違い、**こちらはあなたの
PCが動いていないと実行されません。**

- 7:00にPCがシャットダウン／スリープしていると、その日は配信されません
- スリープからの復帰で実行したい場合は、タスクスケジューラでタスクのプロパティを開き、
  「条件」タブの**「タスクを実行するためにスリープを解除する」にチェック**を入れてください
  （電源設定によっては効かないことがあります）
- 「PCを立ち上げた時に、その日まだ実行していなければ実行する」挙動にしたい場合は、
  「設定」タブの**「スケジュールされた開始時刻を過ぎてからタスクを開始する」にチェック**を
  入れると、起動後に遅れて実行されます

毎朝確実に届かせたいだけなら、リポジトリ直下のGitHub Actions版（Slackのみ・AI要約なし）
を併用するのも手です。あちらはPCの電源に左右されません。
