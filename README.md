# 📰 毎朝ニュース見出しダイジェスト（グローバル経済版）

世界経済・日本経済・株式市場・企業ニュースの**見出し＋元記事リンク**を毎朝
7:00（JST）にSlackへ自動配信します。**Claude API等の要約・生成AIは一切
使いません。** 見出しとリンクの配信のみで、実行コストは完全ゼロ（GitHub
Actions無料枠 + Slack Incoming Webhookのみ）です。要約が欲しい記事は、リンク
を開いて手動でスクリーンショットをClaude.aiのチャットに貼るなどして個別に
依頼してください。

## 配信構成

Slackメッセージは以下の順にセクション分けされます（2026-07-22 run #5で
実際に生存確認・配信確認済み、新着47件→1ソースあたりの上限を8→5件に絞って
配信）:

1. **世界経済**: Reuters (Google News RSS検索経由)・BBC News (World)・
   BBC News (Business)
2. **日本経済**: 内閣府。日銀・財務省はまだ生存確認できるフィードが
   見つかっていない（下記参照）
3. **株式市場**: JPX（日本取引所グループ）マーケットニュース
4. **企業ニュース**: Reuters (Google News RSS検索経由)・CNBC (Finance)
5. **📘 今日覚える経済用語（1つ）**: リポジトリ内に固定した20語の経済用語
   グロッサリー（`sources.py` の `ECONOMIC_TERMS`）から、日付に応じて
   毎日1つを機械的に選ぶだけです。Claude APIなどの生成AIは一切使わないため
   追加コストは発生しません。

## ⚠️ ソースの変遷、まだ埋まっていない枠、AP Newsを採用しなかった理由

当初はNHK主要/経済のRSSを採用していましたが、記事本文の閲覧に「NHK ONE」
への**無料会員登録が必須**になっていることが判明したため不採用にしました
（見出し+リンク配信という前提が成立しないため）。その後ユーザーからの依頼で
「世界経済・日本経済・株式市場・企業ニュース」というグローバル経済フォーカス
の構成に全面刷新し、GitHub Actions run #5（2026-07-22）で実際に生存確認・
配信確認しています。

- **Reuters**: 公式RSS配信を2020年頃に終了しているため、Google News RSS
  検索 (`news.google.com/rss/search?q=site:reuters.com...`) 経由で見出しを
  取得しています（run #5で世界経済/企業ニュース向けクエリとも `entries=100`
  を確認）。Google側の利用条件・キャッシュ挙動に留意してください
- **BBC (World/Business)**: 公式RSSで生存確認済み
- **CNBC (Finance)**: 公式RSSで生存確認済み
- **内閣府**: 公式RSSで生存確認済み
- **JPX（日本取引所グループ）**: 公式のRSS案内ページ (`jpx.co.jp/rss/`) を
  自動発見した結果、`markets_news.xml`（マーケットニュース、19件）が生存
  確認できたため採用。他に見つかった `site-updates.xml`（サイト更新通知）
  や `equities-suspended.xml`（売買停止銘柄）はニュースとして不適切なため
  採用していません
- **IMF**: `rss-list/feed?category=WHATSNEW` はHTTP200を返すものの、実際に
  XMLとしてパースできない不正なフィードだったため不採用にしました
- **日本銀行 / 財務省 / OECD**: 公式のRSS案内ページを`DISCOVERY_PAGES`に
  登録して自動発見を試みましたが、run #5時点では見つかっていません
  （日銀の案内ページは404、財務省のページはRSSリンクが検出できず、OECDは
  ドメイン自体が名前解決できませんでした）。推測でURLを補うことはせず、
  今後の`workflow_dispatch`実行で再度自動発見を試みる運用にしています
- **AP News**: 公式RSSを終了しており、見つかる代替は非公式のサードパーティ
  RSS生成サービスのみでした。ToS上のリスクがあるため採用していません。
  公式RSSが復活すれば追加を検討してください

**本番運用の前に必ず以下を実行してください:**

1. Slackに届いたリンクを実際に数件開き、会員登録なしで読めるか目視確認する
   （特にBBC/CNBCなど海外メディアの地域制限の有無も含めて）
2. 日銀・財務省・OECDの日本経済/世界経済ソースを追加したい場合は、
   `workflow_dispatch` を再実行して "Check RSS feed liveness" ログの
   discover結果を確認し、見つかったものだけを `sources.py` に追加する
   （推測でURLを追加しないこと）

今後URLが死んだ場合や新しいソースを追加したい場合も、推測でURLを書き換えず、
以下のいずれかで再確認してから `sources.py` を更新してください:

1. Actionsタブから `Morning News Digest` を `workflow_dispatch`（手動実行）し、
   "Check RSS feed liveness (informational)" ステップのログを確認する
2. ローカルでインターネットに出られる環境があれば、以下でも同じ確認ができます:

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
  （例: Yahoo!ニュースRSSはプログラムでの利用・再配信を禁止）。Reutersは
  公式RSSを終了しているためGoogle News RSS検索を経由しており、Googleの
  利用条件にも留意してください。本システムは
  **個人利用・非公開の少人数Slackチャンネルでの利用に限定**してください
- **言語**: BBC/Reuters/IMF/CNBCは英語の見出しになります。日本語ソース
  （内閣府など）と混在する構成である点に留意してください
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
