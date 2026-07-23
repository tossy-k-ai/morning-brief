# 📰 news-digest — 日経朝刊レベルの毎朝ニュースダイジェスト

毎朝10〜15分で読める教養ダイジェストを自動生成し、**Slack配信**と**Obsidian Vault保存**の
両方に届けます。対象読者は投資家ではなく、日本で働く一般的なビジネスパーソンです。

**Anthropic API・APIキーは使用しません。** AI処理は Claude Code の headless モード
（`claude -p`）を外部プロセスとして呼び出す方法のみで行うため、Claude Proサブスクリプションの
範囲で運用できます（従量課金は発生しない想定）。

このプロジェクトは `morning-brief` リポジトリのサブフォルダですが、**GitHub Actionsではなく
Windowsタスクスケジューラで、あなたのローカルPC上で動かす前提**です。実行に必要なもの
（Python、Claude Code CLI、Obsidian）はすべてローカルにインストールされている必要があります。

---

## アーキテクチャ（疎結合・3段構成）

```
[STEP 1] src/fetch_rss.py
   RSS取得 → data/articles.json に書き出す
        ↓
[STEP 2] src/generate_summary.py
   claude -p を subprocess で1回だけ呼ぶ
   articles.json + prompts/summarize.md を渡す
        → data/summary.md を生成
        ↓
[STEP 3] src/distribute.py
   summary.md を読み込み
   ├→ Slack へ配信
   └→ Obsidian Vault へ保存
```

各STEPは単体で実行・テストできます（`python src/fetch_rss.py` など）。STEP間の受け渡しは
ファイル（`articles.json` / `summary.md`）で行うため、STEP2やSTEP3が失敗してもSTEP1の
結果は残り、そこから再実行できます。

---

## ✅ RSS生存確認 済み（2026-07-23、GitHub Actionsで実施）

このコードを書いた環境（クラウド上のLinuxサンドボックス）では直接RSSへアクセスできな
かったため、`.github/workflows/news-digest-check.yml`（`workflow_dispatch`専用、実際の
配信は行わない検証用ワークフロー）をGitHub Actions上で実行して確認しました。7ソース
すべて `[OK]`（HTTP200・パース可能）です:

| ソース | 件数 |
|---|---|
| Google News (主要) | 30 |
| Google News (経済) | 101 |
| Google News (ビジネス) | 62 |
| Google News (AI) | 100 |
| ITmedia (速報) | 50 |
| ITmedia (AI+) | 20 |
| ITmedia ビジネスオンライン | 20 |

### ⚠️ ただしGoogle News系4本は「リンクの自動解決」に失敗する

Google Newsの記事リンク（`news.google.com/rss/articles/...`）を実記事URLに解決しようと
試みましたが、4本とも失敗しました。現在のGoogle Newsのリダイレクトは単純なHTTPリダイ
レクトではなく、中間ページのJavaScriptで実記事へ飛ばす方式になっているため、
`requests`ライブラリでは追跡できません。

- **実害**: 人間がSlack/Obsidianでリンクを実際にクリックする分には問題ありません
  （ブラウザがJSを実行して正しく実記事に飛びます）。困るのは、保存されるURL自体が
  Googleの中間URLのままになる、という点だけです
- Google Newsのタイトルには「見出し - 発信元名」の形で発信元が含まれているため
  （例:「... - ロイター」「... - BBC」）、AIが要約する際のソース表記自体には支障
  ありません
- `fetch_rss.py` の `resolve_google_news_link()` は今後Google側の仕様が変わった場合
  に備えて解決ロジックを残してありますが、現時点では実質的に何もしていません
  （常に元のGoogle NewsのURLがそのまま使われます）

再確認したい場合は、Actionsタブから `news-digest RSS check` を `workflow_dispatch`
（手動実行）するか、以下をローカルで実行してください:

```bash
pip install -r requirements.txt
python check_feeds.py
```

---

## セットアップ手順（Windows）

### 1. 前提ソフトウェアの確認

- Python 3.10以降がインストール済みで `python` コマンドが使えること
- `claude` コマンドが使えること（Claude Code CLI がインストール済みで、
  **Claude Pro/Maxアカウントでログイン済み**であること。`ANTHROPIC_API_KEY` は
  設定しないこと — 設定されているとAPI課金経由の認証が優先されてしまう場合があります）
- コマンドプロンプトやPowerShellで以下を実行し、正常に応答が返ることを確認する:

  ```
  claude -p "こんにちは" --output-format json
  ```

### 2. 依存パッケージのインストール

```
pip install -r requirements.txt
```

### 3. RSSの生存確認（上記「まだ検証できていないこと」を参照）

```
python check_feeds.py
```

### 4. Slack Webhookの設定

1. Slack Appを作成し Incoming Webhook を有効化する（`https://api.slack.com/apps`）
2. `.env.example` を `.env` にコピーし、`SLACK_WEBHOOK_URL` に発行されたURLを設定する

### 5. Obsidian Vaultパスの設定

`config.yaml` の `obsidian.vault_path` を、実際のVaultパスに書き換えてください。
既存の「投資分析」フォルダとは別の、このダイジェスト専用のフォルダを指定する想定です
（デフォルトは `C:/Users/俊宏/ObsidianVault/News Digest`）。

### 6. 各STEPを単体でテストする

```
python src\fetch_rss.py
python src\generate_summary.py
python src\distribute.py
```

`data\articles.json` → `data\summary.md` の順に生成され、`distribute.py` でSlack投稿と
Obsidian保存が行われます。それぞれ単体で再実行できるので、STEP2がおかしければ
`data\articles.json` を消さずにプロンプトだけ調整して再実行、といった使い方ができます。

### 7. `run_daily.bat` を手動実行して確認する

```
run_daily.bat
```

`logs\YYYY-MM-DD.log` にSTEP1〜3の実行ログが残ります。正常終了すればタスクスケジューラ
登録に進んでください。

### 8. Windowsタスクスケジューラへの登録

1. 「タスクスケジューラ」を開く
2. 「基本タスクの作成」→ 名前を付ける（例: `news-digest daily`）
3. トリガー: 「毎日」→ 開始時刻 `07:00`
4. 操作: 「プログラムの開始」→ プログラム/スクリプトに `run_daily.bat` のフルパスを指定
   （例: `C:\Users\俊宏\news-digest\run_daily.bat`）
5. 「開始（オプション）」に `run_daily.bat` があるフォルダのパスを指定する
   （相対パスの解決のため。バッチ内でも `cd /d %~dp0` しているので必須ではないが、
   念のため設定しておくと安全）
6. 完了後、タスクを右クリック→「実行」で手動テストし、`logs` フォルダにログが
   出るか確認する

---

## 🚨 headless実行が無人で止まらないための対策（実装済み）

| 停止要因 | このプロジェクトでの対策 |
|---|---|
| セッション再開ダイアログ | `--no-session-persistence` でセッション保存自体を無効化 |
| ツール権限の確認待ち | `--tools ""` で全ツールを無効化（テキスト生成のみなので不要）。加えて `--permission-mode dontAsk` |
| 応答が返らない | `config.yaml` の `claude.timeout_seconds`（既定600秒）で `subprocess.run` にtimeoutを設定。超過時はSTEP2失敗として扱う |
| コンテキスト肥大・無関係ファイルの読み込み | `.claude_work/`（このプロジェクト専用の空ディレクトリ、実行のたびに使い回す）を `cwd` にして `claude -p` を実行し、`morning-brief`本体などの無関係なCLAUDE.md/ファイルを読ませない |

### `claude -p --help` で確認した実際のフラグ（2026-07-22時点）

指示書のサンプルコードにあった `--max-turns` は、確認した現行バージョンには
**存在しませんでした**。代わりに `--max-budget-usd`（ドル上限、`--print`専用）を
安全弁として使っています。`--permission-mode dontAsk` は実在する値でした
（他の選択肢: `acceptEdits` / `auto` / `bypassPermissions` / `manual` / `plan`）。

`--bare` フラグ（CLAUDE.md自動探索等を無効化）も検討しましたが、**認証が
`ANTHROPIC_API_KEY` かAPIキーヘルパーのみに固定される**（OAuth/キーチェーン認証が
使えなくなる）ため、Proサブスク認証を前提とする本プロジェクトでは使っていません。
`.claude_work/` を専用の作業ディレクトリにすることで同様の効果を得ています。

バージョンが上がるとフラグが変わる可能性があります。動かない場合は
`claude -p --help` を再確認してください。

---

## 🤖 プロンプト設計についての注意（要レビュー）

指示書の「10件の選定」の内訳（今日最重要5件・経済企業3件・AI2件 = 10件）と、
出力テンプレートの4セクション（今日最重要／国内・国際／経済・企業／AI・テクノロジー）
の対応関係が、指示書の記述だけでは一意に決まりませんでした（5+3+2=10で
「国内・国際」に割り当てる件数が明記されていない）。

このプロジェクトでは以下のように解釈して `prompts/summarize.md` を書いています:

- 「今日最重要」= 全カテゴリ横断で最も重要な5件（ジャンル不問）
- 「経済・企業」「AI・テクノロジー」= 今日最重要に選ばれなかったものの中からそれぞれ
  3件・2件
- 「国内・国際」= 上記8件に入らなかったが紹介する価値がある記事があれば追加
  （水増し禁止なので、無い日は空でよい）

意図と違う場合は `prompts/summarize.md` を書き換えてください（AIプロンプトは
コードと分離してあるので、ここだけの修正で挙動を変えられます）。

---

## 🚨 失敗に気づくための仕組み

- STEP1〜3のいずれかが失敗すると `run_daily.bat` はそこで打ち切られ、
  `logs\YYYY-MM-DD.log` に失敗内容が記録されます
- STEP3（配信）内でSlack投稿とObsidian保存のどちらかが失敗した場合、
  Webhookが生きていれば **Slackにエラー内容を投稿**します
- 正常時も「取得◯件 → 鮮度フィルタ後◯件 → 重複除去後◯件」（STEP1）、
  「◯件の記事からsummary.mdを生成」（STEP2）をログに残すので、0件の日と
  障害の日を区別できます

---

## 🔐 必要な環境変数

| キー | 用途 | 設定場所 |
|---|---|---|
| `SLACK_WEBHOOK_URL` | Slackへの配信 | `.env`（`run_daily.bat` が読み込む） |

`ANTHROPIC_API_KEY` は設定しないでください。Claude Code CLIがClaude Proアカウントの
ログインセッションで動くことを前提にしています。

---

## ⚠️ 利用上の注意

- **API不使用**: `anthropic` パッケージ・APIキーは使いません。AI処理は `claude -p`
  の外部呼び出しのみです
- **推測禁止**: 情報が足りない記事は要約せず「要約なし（本文未取得のため）」と明記します
  （`prompts/summarize.md` に明記済み）
- **著作権**: 記事本文の全文保存・再配布はしません。個人利用・非公開チャンネルでの
  利用に限定してください
- **RSS利用規約**: 使用する各RSS提供元の利用規約を確認してください
- **推測でURLを埋めない**: `check_feeds.py` で生存確認できないRSSは採用しないでください
- **堅牢性**: 一部のRSSソースが取得できなくても、他のソースの収集・配信は継続します

---

## 🗂 ファイル構成

```
news-digest/
├── config.yaml              # RSSソース・モデル・パス等の設定
├── prompts/
│   └── summarize.md         # AIプロンプト（別ファイル化）
├── src/
│   ├── config_loader.py     # config.yaml読み込み共通処理
│   ├── fetch_rss.py         # STEP1
│   ├── generate_summary.py  # STEP2（claude -p 呼び出し）
│   ├── distribute.py        # STEP3
│   ├── slack_client.py      # Slack投稿・Markdown→Block Kit変換
│   ├── obsidian_writer.py   # Obsidian保存
│   └── dedupe.py            # 重複除去ロジック
├── data/                    # articles.json / summary.md (gitignore対象)
├── logs/                    # 実行ログ (gitignore対象)
├── check_feeds.py           # RSS生存確認スクリプト
├── run_daily.bat            # タスクスケジューラ用
├── requirements.txt
├── .env.example             # SLACK_WEBHOOK_URL
└── README.md
```
