"""毎朝ニュース見出しダイジェスト — RSSソース定義。

重要な注意 (2026-07-22 実装時点):
    このファイルの候補URLは、実装を行ったサンドボックス環境の組織ネットワーク
    ポリシーにより outbound アウトバウンド通信が全面的にブロックされていたため
    (NHK・Wikipedia・google.com など、テストした全ドメインで CONNECT 拒否 / 403)、
    実際に HTTP アクセスして生存確認することが**できなかった**。

    WebSearch による裏付け調査では、NHK は 2025年10月の「NHK ONE」移行に伴い
    無料テキストニュースを整理しており、旧来の cat0.xml / cat5.xml 系のRSSが
    現時点 (2026-07) で生きているかは不明。

    そのため、本番運用前に必ず以下のいずれかの方法で実際の生存確認を行うこと:
        1. GitHub Actions で `workflow_dispatch` を一度手動実行し、
           "Check RSS feed liveness" ステップのログを確認する
        2. インターネットに出られるローカル環境で `python check_feeds.py --discover`
           を実行する

    生存が確認できたら、動作確認結果をこのファイルのコメントに追記し、
    死んでいるURLは削除・置き換えること (推測でURLを追加しないこと)。
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Source:
    name: str
    url: str
    verified: bool = False  # check_feeds.py で生存確認できたら True にする
    note: str = ""


# --- 候補ソース (すべて未検証。上記の手順で確認してから運用すること) --------
SOURCES = [
    Source(
        name="NHK 主要",
        url="https://www.nhk.or.jp/rss/news/cat0.xml",
        verified=False,
        note="仕様書記載の候補。未検証 (2026-07-22時点)。",
    ),
    Source(
        name="NHK 経済",
        url="https://www.nhk.or.jp/rss/news/cat5.xml",
        verified=False,
        note="仕様書記載の候補。未検証 (2026-07-22時点)。",
    ),
    Source(
        name="NHK 主要 (www3, 旧ドメイン代替候補)",
        url="https://www3.nhk.or.jp/rss/news/cat0.xml",
        verified=False,
        note="複数の技術ブログで言及されている旧URL形式。未検証。"
        "www.nhk.or.jp 側が死んでいた場合の代替候補として残す。",
    ),
]

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
