"""毎朝ニュース見出しダイジェスト — RSSソース定義。

検証結果 (2026-07-22、GitHub Actions workflow_dispatch run #1 で確認済み):
    - NHK 主要 (www.nhk.or.jp/rss/news/cat0.xml): [OK] 7件
      リンクは新ドメイン https://news.web.nhk/newsweb/na/... 形式
    - NHK 経済 (www.nhk.or.jp/rss/news/cat5.xml): [OK] 58件
    - NHK 主要 (www3.nhk.or.jp/rss/news/cat0.xml): [OK] 7件だが「NHK 主要」と
      同一記事の別ドメインリンクで、重複配信の原因になったため候補から削除した
      (リンクURL一致の重複除外をすり抜けてSlackに同じ見出しが2回届いた)。
    - discover機能で 首相官邸 (kantei.go.jp/index-jnews.rdf)・厚労省・内閣府の
      RSSも生存確認できたが、本仕様のNHK主要+経済という要件外なので採用していない。
      gov-online.go.jp/rss/ は403で取得不可だった。

    今後URLが死んだ場合は、推測で書き換えず `python check_feeds.py --discover`
    で再確認してから更新すること。
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Source:
    name: str
    url: str
    verified: bool = False  # check_feeds.py で生存確認できたら True にする
    note: str = ""


# --- 採用ソース (2026-07-22 に check_feeds.py --discover で生存確認済み) ----
SOURCES = [
    Source(
        name="NHK 主要",
        url="https://www.nhk.or.jp/rss/news/cat0.xml",
        verified=True,
        note="2026-07-22 確認: HTTP 200, entries=7, title/link/published/summaryあり。",
    ),
    Source(
        name="NHK 経済",
        url="https://www.nhk.or.jp/rss/news/cat5.xml",
        verified=True,
        note="2026-07-22 確認: HTTP 200, entries=58, title/link/published/summaryあり。",
    ),
]

# www3.nhk.or.jp/rss/news/cat0.xml も生存していたが、「NHK 主要」と同一記事を
# 別ドメインのリンクで配信するだけで、リンクURL一致の重複除外をすり抜けて
# Slackに同じ見出しが2回届く原因になったため、採用ソースからは外している。

# 時事通信の無料公開RSSは存在が未確認のため候補に含めない (仕様書の指示通り)。
# 経済ニュースの追加ソースが必要な場合は、DISCOVERY_PAGES を使って
# 公的機関 (政府広報・各省庁) のRSSを探索し、生存確認できたものだけを
# SOURCES に追加すること。

# HTMLから <link type="application/rss+xml"> や .xml/.rdf へのリンクを
# 自動探索するための起点ページ。check_feeds.py --discover が使用する。
# (URLそのものではなく「RSSについて」の案内ページなので、推測URLではない)
DISCOVERY_PAGES = [
    "https://www.nhk.or.jp/news/",
    "https://www.kantei.go.jp/rss.html",
    "https://www.gov-online.go.jp/rss/",
    "https://www.mhlw.go.jp/rss/index.html",
    "https://www.cao.go.jp/rss/",
]
