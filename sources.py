"""毎朝ニュース見出しダイジェスト — RSSソース定義。

変更履歴:
  2026-07-22 (1): NHK 主要/経済 のRSSは生存確認できたが (run #1, #2)、ユーザーが
      実際にリンクを開いたところ本文閲覧に「NHK ONE」への会員登録が必須に
      なっていることが判明した。見出し+リンク配信という本システムの前提が
      成立しないため、NHKをSOURCESから外した。
  2026-07-22 (2): 代替候補としてITmedia/時事通信をDISCOVERY_PAGES経由で
      自動発見し、GitHub Actions run #3 で実際に生存確認した。結果:
        - 時事通信 人気ランキング (jiji.com/rss/ranking.rdf):
          jiji.comトップページから自動発見。entries=10。例:
          「ＮＨＫ映画、公開差し止め請求 戦後８０年ドラマ巡り遺族側―東京地裁」
          など社会・政治系も含む総合ニュース。published/summaryは提供されず、
          見出し+リンクのみ。
        - ITmedia NEWS(速報)/トップストーリー/国内ニュースは、いずれも
          ITmedia NEWSの同一記事プールを返すだけで内容がほぼ重複するため、
          代表として business.xml (ビジネスオンライン) のみ採用した。
      いずれも会員登録なしで本文を読める想定だが、RSS自体の生存確認では
      判定できないため、ユーザーが実際にSlackのリンクを開いて確認すること。
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

# --- 採用ソース (2026-07-22, GitHub Actions run #3 で生存確認済み) ---------
SOURCES = [
    Source(
        name="時事通信 (人気ランキング/主要ニュース代替)",
        url="https://www.jiji.com/rss/ranking.rdf",
        verified=True,
        note="2026-07-22 run #3確認: HTTP200, entries=10, title/linkあり "
        "(published/summaryは提供されない)。時事通信トップページから自動発見。"
        "社会・政治系も含む総合ニュース。会員登録なしで読めるはずだが、"
        "見出しがランキング(人気順)なので日々の入れ替わりはNHKほど多くない点に注意。",
    ),
    Source(
        name="ITmedia ビジネスオンライン (経済)",
        url="https://rss.itmedia.co.jp/rss/2.0/business.xml",
        verified=True,
        note="2026-07-22 run #3確認: HTTP200, entries=20, title/link/published/"
        "summaryあり。公式RSS利用条件で私的利用は無償と明記。会員登録不要。",
    ),
]

# ITmedia NEWS(速報)/トップストーリー/国内ニュースは、いずれもITmedia NEWSの
# 同一記事プールを返すだけで内容がほぼ重複するため採用しなかった。
# IT/テクノロジー寄りの記事をもっと増やしたい場合は、以下も生存確認済み:
#   https://rss.itmedia.co.jp/rss/2.0/news_domestic.xml (国内, entries=30)
#   https://rss.itmedia.co.jp/rss/2.0/news_bursts.xml (速報, entries=50)

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
