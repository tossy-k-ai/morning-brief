# 📰 毎朝ニュース見出しダイジェスト

国内の主要ニュース・経済ニュースの**見出し＋元記事リンク**を毎朝7:00（JST）に
Slackへ自動配信します。**Claude API等の要約・生成AIは一切使いません。**
見出しとリンクの配信のみで、実行コストは完全ゼロ（GitHub Actions無料枠 + Slack
Incoming Webhookのみ）です。要約が欲しい記事は、リンクを開いて手動でスクリーン
ショットをClaude.aiのチャットに貼るなどして個別に依頼してください。

---

## ⚠️ 最初に必ず読むこと（RSS URLは未検証です）

このリポジトリの `sources.py` に書かれているRSS候補URL（NHK系）は、**実際に
HTTPアクセスして生存確認できていません。**

理由: この実装を行った開発用サンドボックス環境では、組織のネットワークポリシー
により外部への一般アウトバウンド通信（curl・WebFetchなど）が全面的にブロック
されており（NHK・Wikipedia・google.comなど、テストした全ドメインで拒否）、
候補URLに実際にアクセスして確認する手段がありませんでした。あわせて、
WebSearchでの裏付け調査では「NHKは2025年10月の『NHK ONE』移行に伴い無料
テキストニュースを整理した」との情報があり、旧来の `cat0.xml` / `cat5.xml` が
現在も生きているかは不明です。

そのため、**本番運用の前に必ず以下を実行してください**（GitHub Actionsの
実行環境はインターネットに出られるので、そちらで確認します）:

1. GitHub Secretsに `SLACK_WEBHOOK_URL` を登録した状態で、Actionsタブから
   `Morning News Digest` ワークフローを `workflow_dispatch`（手動実行）する
2. 実行ログの **"Check RSS feed liveness (informational)"** ステップを開き、
   `check_feeds.py --discover` の出力を確認する
   - `[OK]` が1件も無ければ、`main.py` 実行時にSlackへエラー通知が届く
     （下記「失敗に気づくための仕組み」参照）
3. `[NG]` だったURLは `sources.py` の `SOURCES` から削除し、`[OK]` だった
   URL（`--discover` で自動発見したものも含む）に置き換える
   - 推測でURLを追加しないこと。必ず `check_feeds.py` で確認できたものだけを
     使うこと
4. 修正後、もう一度 `workflow_dispatch` で確認する

ローカルでインターネットに出られる環境があれば、以下でも同じ確認ができます:

```bash
pip install -r requirements.txt
python check_feeds.py --discover
```

---

## 🚀 セットアップ

### 1. Slack Incoming Webhookを取得する

1. Slack Appを作成（https://api.slack.com/apps → "Create New App"）
2. "Incoming Webhooks" を有効化し、投稿したいチャンネルにWebhookを追加
3. 発行された `https://hooks.slack.com/services/...` のURLを控える

### 2. GitHub Secretsに登録する

リポジトリの Settings → Secrets and variables → Actions → New repository secret

| Key | Value |
|---|---|
| `SLACK_WEBHOOK_URL` | 手順1で取得したWebhook URL |

### 3. 手動実行して確認する

Actionsタブ → "Morning News Digest" → "Run workflow" で `workflow_dispatch` を
実行し、Slackにメッセージが届くか確認する（上記「RSS URLは未検証」の手順も
あわせて実施すること）。

### 4. ローカルでのテスト

```bash
cp .env.example .env
# .env に実際のSLACK_WEBHOOK_URLを設定する

pip install -r requirements.txt
export $(cat .env | xargs)   # または direnv 等で読み込む
python main.py
```

---

## 🚨 失敗に気づくための仕組み

- RSSが全ソース失敗、またはSlack投稿自体が失敗した場合、Webhookが生きている
  限り**Slackにエラー内容を投稿**します
- 正常時も「本日は新着◯件」と件数を表示するので、0件の日と障害の日を区別
  できます
- GitHub Actionsのワークフロー自体が失敗（exit code 非0）した場合、GitHubから
  リポジトリの通知設定に従って**失敗通知メール**が届きます。届くようにするには:
  1. https://github.com/settings/notifications を開く
  2. "Actions" の通知設定で、少なくとも自分がwatchしているリポジトリの
     失敗時にメールが届く設定になっているか確認する
  3. このリポジトリを "Watching" にしていない場合は、リポジトリ右上の
     "Watch" から通知対象に含める

---

## ⏰ スケジュール実行について

- cronは **UTC** 基準です。7:00 JST = **22:00 UTC** として `0 22 * * *` を
  設定しています
- GitHub Actionsのスケジュール実行は負荷状況により**数分〜十数分遅れる**、
  または**稀にスキップされる**ことがあります（GitHub Actionsの仕様）。
  7:00ちょうどの配信は保証されません

### ⚠️ 60日間コミットが無いとcronが自動停止する問題への対策

GitHub Actionsのスケジュール実行は、**リポジトリに約60日間アクティビティ
（コミット等）が無いと自動的に無効化されます**。放置すると毎朝の配信が
静かに止まります。

このリポジトリでは、ワークフロー実行のたびに `last_run.txt` に実行日時を
書き込んで自動コミット・pushすることでリポジトリを"アクティブ"に保って
います（`.github/workflows/digest.yml` の "Keep repository active" ステップ）。
このステップが何らかの理由で失敗し続ける場合は、**月1回程度**リポジトリに
手動でコミットする（例: READMEを少し編集する）などして自動停止を防いで
ください。

---

## 🔐 必要なSecrets

| キー | 用途 | 必須 |
|---|---|---|
| `SLACK_WEBHOOK_URL` | Slackへの配信 | ◎ |

Claude API等の生成AIは使用しないため、APIキーの類は一切不要です。

---

## ⚠️ 利用上の注意

- **RSS利用規約**: 使用するRSS提供元の利用規約を必ず確認してください。
  提供元によってはプログラムによる再配信を禁じている場合があります
  （例: Yahoo!ニュースRSSはプログラムでの利用・再配信を禁止）。本システムは
  **個人利用・非公開の少人数Slackチャンネルでの利用に限定**してください
- **著作権**: 記事本文の全文保存・再配布は行いません。扱うのは見出し・
  RSSのdescription（原文のまま）・元記事へのリンクのみです
- **推測でURLを追加しない**: `check_feeds.py` で生存確認できないRSSは
  採用しないでください
- **堅牢性**: 一部のRSSソースが取得できなくても、他のソースの配信は
  継続します
- **コスト**: GitHub Actions無料枠 + Slack Incoming Webhookのみで、
  API課金は一切発生しません（完全無料構成）

---

## 📁 構成

| ファイル | 役割 |
|---|---|
| `main.py` | 収集〜整形〜配信〜失敗通知の一連の処理 |
| `sources.py` | RSSソース定義（候補URLと検証状況をコメントで記録） |
| `slack_formatter.py` | Block Kit変換・Webhook投稿・エラー通知 |
| `check_feeds.py` | RSS生存確認スクリプト（`--discover` でHTML内のRSSリンクも自動探索） |
| `.github/workflows/digest.yml` | cron設定＋アクティビティ維持コミット |
| `requirements.txt` | Python依存パッケージ |
| `.env.example` | ローカルテスト用の環境変数サンプル |
