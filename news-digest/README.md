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
   claude -p を subprocess で1回だけ呼ぶ（プロンプトは stdin で渡す）
   articles.json + prompts/summarize.md を渡す
        → data/summary.json（今日の1面・カテゴリ面の構造化データ）を生成
          入力に無いURLの記事は破棄し、出典リンクが必ず原文URLになるよう検証する
        ↓
[STEP 3] src/distribute.py
   summary.json を読み込み
   ├→ Obsidian Vault へ「新聞面」Markdownを保存（src/newspaper.py で整形。控えを data/summary.md に保存）
   └→ Slack へ「今日の1面」の見出しだけを通知（obsidian:// リンク付き）
```

各STEPは単体で実行・テストできます（`python src/fetch_rss.py` など）。STEP間の受け渡しは
ファイル（`articles.json` / `summary.json`）で行うため、STEP2やSTEP3が失敗してもSTEP1の
結果は残り、そこから再実行できます。

### 新聞面の構成（Obsidian: `Downloads/wiki/daily/YYYY-MM-DD.md`）

1. 紙名（`config.yaml` の `obsidian.paper_title`）と日付
2. **今日の1面**: 最重要3〜5件。見出し＋2〜3文の要約＋出典リンク
3. カテゴリ面（`category_order` の順）: 採用・人材 → 投資・マーケット → 経済・企業 →
   AI・テクノロジー → 国内・国際。各最大5件、見出し＋1〜2文の要約＋出典リンク
4. 今日の言葉（キーワード解説）

英語記事（`lang: "en"` のソース）も見出し・要約は日本語で出力し、出典リンクは原文URL、
出典名の後ろに「（英語記事）」と付けます。見出し・要約には株価指数の水準・騰落幅の数値を
書かない方針です（`prompts/summarize.md` に明記。混入した場合はSTEP2のログに `[WARN]` が出ます）。

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

### 2026-11-01 追加ソース（ローカルで `check_feeds.check_source` により確認、全て `[OK]`）

| ソース | カテゴリ | 備考 |
|---|---|---|
| Google News (採用・求人) | recruitment | `採用 OR 求人 OR 転職 when:1d` |
| Google News (人材・雇用・人事) | recruitment | `人材 OR 雇用 OR 人事 when:1d` |
| HRzine | recruitment | descriptionなし（見出しのみ） |
| Google News (株式市場) | markets | `株式市場 when:1d` |
| Google News (為替) | markets | `円相場 OR 為替相場 when:1d` |
| Google News (企業決算) | markets | `企業決算 OR 決算発表 when:1d` |
| CNBC (Top News) / CNBC (Markets) | markets (英語) | 実URLが直接取れる |
| MarketWatch (MarketPulse) | markets (英語) | descriptionなし |
| Google News EN (Reuters markets) | markets (英語) | Reuters公式RSSは廃止済みのため代替 |

既存7ソースも同日に再確認し、全て `[OK]` でした。

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

`config.yaml` の `obsidian.vault_path` に、ノートを保存するフォルダを指定します
（現在は wiki Vault の daily フォルダ `C:/Users/俊宏/Downloads/wiki/daily`）。
Slack通知の `obsidian://open` リンクは `obsidian.vault_name`（`wiki`）と
`obsidian.note_folder`（`daily`）から組み立てます。保存先を変えたらこの2つも合わせてください。

### 6. 各STEPを単体でテストする

```
python src\fetch_rss.py
python src\generate_summary.py
python src\distribute.py
```

`data\articles.json` → `data\summary.json` の順に生成され、`distribute.py` でObsidian保存と
Slack見出し通知が行われます。それぞれ単体で再実行できるので、STEP2がおかしければ
`data\articles.json` を消さずにプロンプトだけ調整して再実行、といった使い方ができます。
（`distribute.py` は `summary.json` の日付が本日でなければ中止します。前日分の再配信防止のため）

`run_daily.bat` は **ASCII文字だけで書いてください**。cmd.exe は UTF-8 の多バイト文字を含む
行を読み違え（バイト位置がずれ、コメントの断片がコマンドとして実行される）、`.env` の
読み込みループまで壊れることを 2026-11-01 に確認しています。

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

## 🤖 プロンプト設計（2026-11-01 改訂）

`prompts/summarize.md` は、Markdownではなく**JSON**（`front_page` / `sections` / `keyword`）を
出力させます。整形はプログラム側（`src/newspaper.py`）で行うため、新聞面のレイアウトを
変えてもプロンプトは変えなくて済みます。カテゴリ一覧は `config.yaml` の
`category_order` / `category_labels` から自動でプロンプトに差し込まれます。

- 今日の1面: 全カテゴリ横断で3〜5件
- カテゴリ面: 1面以外から各カテゴリ最大5件（水増し禁止、無ければ空）
- 情報不足の記事は `summary: null` →新聞面では「要約なし（本文未取得のため）」または見出しのみ

意図と違う場合は `prompts/summarize.md` を書き換えてください。

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
│   ├── newspaper.py         # summary.json → 新聞面Markdown / obsidian:// リンク
│   ├── slack_client.py      # Slack投稿（1面の見出し通知）
│   ├── obsidian_writer.py   # Obsidian保存
│   └── dedupe.py            # 重複除去ロジック
├── data/                    # articles.json / summary.json / summary.md (gitignore対象)
├── logs/                    # 実行ログ (gitignore対象)
├── check_feeds.py           # RSS生存確認スクリプト
├── run_daily.bat            # タスクスケジューラ用
├── requirements.txt
├── .env.example             # SLACK_WEBHOOK_URL
└── README.md
```
