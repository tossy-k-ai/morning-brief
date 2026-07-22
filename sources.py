"""毎朝ニュース見出しダイジェスト — RSSソース定義。

変更履歴:
  2026-07-22 (1): NHK 主要/経済 のRSSは生存確認できたが (run #1, #2)、ユーザーが
      実際にリンクを開いたところ本文閲覧に「NHK ONE」への会員登録が必須に
      なっていることが判明した。見出し+リンク配信という本システムの前提が
      成立しないため、NHKをSOURCESから外した。
  2026-07-22 (2): 代替候補として ITmedia (会員登録不要の無料IT/ビジネスニュース、
      公式RSS利用条件ページで個人利用は無償と明記) を追加。時事通信
      (jiji.com) もRSS提供の記載はあるが具体的なフィードURLが特定できな
      かったため、DISCOVERY_PAGES 経由で自動発見して確認する。
      推測でURLを追加しないこと。必ず check_feeds.py --discover で確認して
      からこのファイルを更新すること。
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Source:
    name: str
    url: str
    verified: bool = False  # check_feeds.py で生存確認できたら True にする
    note: str = ""


# --- NHKは会員登録が必要になったため不採用 (2026-07-22、ユーザー確認) ---------
# www.nhk.or.jp/rss/news/cat0.xml / cat5.xml 自体はRSSとして生存しているが、
# リンク先の記事本文が「NHK ONE」への無料会員登録なしに読めなくなっている。
# 見出し+リンクを配信するだけの本システムでは実用にならないため使用しない。

# --- 候補ソース (ITmediaは公式RSS一覧に掲載されている直リンク候補。
#     未検証 — check_feeds.py --discover で確認してから運用すること) --------
SOURCES = [
    Source(
        name="ITmedia NEWS (速報)",
        url="https://rss.itmedia.co.jp/rss/2.0/news_bursts.xml",
        verified=False,
        note="ITmedia公式RSS一覧に掲載。RSS利用条件: 私的利用(RSSリーダー等での"
        "閲覧)は無償、商用利用は要許諾。会員登録なしで記事本文を読める。未検証。",
    ),
    Source(
        name="ITmedia トップストーリー",
        url="https://rss.itmedia.co.jp/rss/2.0/topstory.xml",
        verified=False,
        note="同上。未検証。",
    ),
]

# 時事通信 (jiji.com) はRSS提供している旨の公式ページ
# (https://www.jiji.com/policy/rss.html) は見つかったが、検索では具体的な
# フィードURLまで特定できなかった。推測でURLを書かず、DISCOVERY_PAGES経由で
# 自動発見してから確認すること。時事通信は主要+経済の両方をカバーできる
# 有力な代替候補。

# HTMLから <link type="application/rss+xml"> や .xml/.rdf へのリンクを
# 自動探索するための起点ページ。check_feeds.py --discover が使用する。
# (URLそのものではなく「RSSについて」の案内ページ・トップページなので、
# 推測URLではない)
DISCOVERY_PAGES = [
    "https://www.jiji.com/",
    "https://www.jiji.com/policy/rss.html",
    "https://corp.itmedia.co.jp/media/rss_list/",
    "https://www.kantei.go.jp/rss.html",
    "https://www.mhlw.go.jp/rss/index.html",
    "https://www.cao.go.jp/rss/",
]
