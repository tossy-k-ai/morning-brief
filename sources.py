"""毎朝ニュース見出しダイジェスト — RSSソース定義。

変更履歴:
  2026-07-22 (1): NHK 主要/経済 のRSSは生存確認できたが (run #1, #2)、ユーザーが
      実際にリンクを開いたところ本文閲覧に「NHK ONE」への会員登録が必須に
      なっていることが判明した。見出し+リンク配信という本システムの前提が
      成立しないため、NHKをSOURCESから外した。
  2026-07-22 (2): 代替として時事通信(人気ランキング)+ITmediaビジネスオンラインに
      切り替え、GitHub Actions run #3/#4 で生存確認・配信確認した。
  2026-07-22 (3): ユーザーから「世界経済・日本経済・株式市場・企業ニュース」の
      グローバル経済ニュースダイジェストへの全面刷新を依頼され、時事通信/
      ITmediaを置き換えた。各ソースに category を持たせ、main.py側で
      カテゴリ順にグルーピングして配信する。
      - Reutersは公式RSS配信を終了しているため、Google News RSS検索
        (news.google.com/rss/search) 経由で代替している。
      - AP Newsも公式RSSを終了しており、代替は非公式のサードパーティ生成
        RSSしかない (ToS上のリスクがあるため不採用)。
      - CNBC/BBC/IMFは直リンク候補として追加。JPX/日本銀行/財務省/OECDは
        公式のRSS案内ページをDISCOVERY_PAGESに追加し、自動発見で確認する
        (推測でフィードURLを書かない)。
      本ファイルの verified=False の候補は、check_feeds.py --discover を
      GitHub Actions上で実行して確認してから True に更新すること。
"""

from dataclasses import dataclass
from datetime import date as _date


@dataclass(frozen=True)
class Source:
    name: str
    url: str
    category: str
    verified: bool = False  # check_feeds.py で生存確認できたら True にする
    note: str = ""


# 表示順序 (main.py / slack_formatter.py はこの順にセクションを並べる)
CATEGORY_ORDER = ["世界経済", "日本経済", "株式市場", "企業ニュース"]

# --- NHKは会員登録が必要になったため不採用 (2026-07-22、ユーザー確認) ---------
# --- 時事通信/ITmediaは、よりグローバル経済寄りの構成への刷新依頼により置き換え ---

# Google News RSS検索 (Reutersは2020年頃に公式RSS配信を終了しているため、
# Googleの公開RSS検索インタフェースを経由して見出しを取得する)
_GOOGLE_NEWS_REUTERS_WORLD = (
    "https://news.google.com/rss/search?q=site:reuters.com+when:1d+"
    "(economy+OR+markets+OR+global+economy)&hl=en-US&gl=US&ceid=US:en"
)
_GOOGLE_NEWS_REUTERS_CORP = (
    "https://news.google.com/rss/search?q=site:reuters.com+when:1d+"
    "(earnings+OR+company+OR+corporate)&hl=en-US&gl=US&ceid=US:en"
)

SOURCES = [
    # --- 世界経済 (Reuters・BBC) ---------------------------------------
    Source(
        name="Reuters (Google News経由: 世界経済)",
        url=_GOOGLE_NEWS_REUTERS_WORLD,
        category="世界経済",
        verified=False,
        note="Reutersは公式RSSを終了済みのため、Google News RSS検索で代替。"
        "未検証 — check_feeds.py --discover で確認すること。",
    ),
    Source(
        name="BBC News (World)",
        url="https://feeds.bbci.co.uk/news/world/rss.xml",
        category="世界経済",
        verified=False,
        note="BBC公式RSS。未検証。",
    ),
    Source(
        name="BBC News (Business)",
        url="https://feeds.bbci.co.uk/news/business/rss.xml",
        category="世界経済",
        verified=False,
        note="BBC公式RSS。未検証。",
    ),
    Source(
        name="IMF (What's New)",
        url="https://www.imf.org/en/rss-list/feed?category=WHATSNEW",
        category="世界経済",
        verified=False,
        note="IMF公式RSS。世界経済見通し等。未検証。",
    ),
    # --- 日本経済 (日銀・財務省・内閣府) --------------------------------
    Source(
        name="内閣府",
        url="https://www.cao.go.jp/rss/news.rdf",
        category="日本経済",
        verified=True,
        note="2026-07-22 run #1のdiscover機能で生存確認済み: HTTP200, entries=10,"
        " title/link/publishedあり(summaryなし)。GDP・景気動向等の政府発表。",
    ),
    # --- 企業ニュース (Reuters) ------------------------------------------
    Source(
        name="Reuters (Google News経由: 企業ニュース)",
        url=_GOOGLE_NEWS_REUTERS_CORP,
        category="企業ニュース",
        verified=False,
        note="Reutersは公式RSSを終了済みのため、Google News RSS検索で代替。"
        "未検証。",
    ),
    Source(
        name="CNBC (Finance)",
        url="https://www.cnbc.com/id/10000664/device/rss/rss.html",
        category="企業ニュース",
        verified=False,
        note="CNBC公式RSS (Financeカテゴリ)。米国市場・企業ニュース。未検証。",
    ),
]

# AP Newsは公式RSS配信を終了しており、代替は非公式のサードパーティRSS生成
# サービスしか見つからなかった (rss.app等)。ToS上のリスクがあるため不採用。
# 生存確認が取れる公式RSSが見つかれば追加を検討する。

# HTMLから <link type="application/rss+xml"> や .xml/.rdf へのリンクを
# 自動探索するための起点ページ。check_feeds.py --discover が使用する。
# (URLそのものではなく「RSSについて」の公式案内ページなので、推測URLではない)
DISCOVERY_PAGES = [
    "https://www.jpx.co.jp/rss/",  # 株式市場: 日本取引所グループ公式RSS案内
    "https://www.boj.or.jp/rss.htm",  # 日本経済: 日本銀行公式RSS案内
    "https://www.mof.go.jp/about_mof/rss/index.html",  # 日本経済: 財務省公式RSS一覧
    "https://www.mof.go.jp/english/rss.htm",  # 日本経済: 財務省 英語版RSS一覧
    "https://search.oecd.org/rssfeeds/",  # 世界経済: OECD公式RSS案内
]


# --- 今日覚える経済用語 (Claude API不使用。固定リストから日替わりで選ぶ) -------
ECONOMIC_TERMS = [
    {"term": "インフレーション（インフレ）", "definition": "物価が持続的に上昇し、貨幣の購買力が低下すること。"},
    {"term": "デフレーション（デフレ）", "definition": "物価が持続的に下落すること。"},
    {"term": "GDP（国内総生産）", "definition": "一定期間に国内で生み出された財・サービスの付加価値の合計。"},
    {"term": "金融政策", "definition": "中央銀行が物価や景気を安定させるために金利や資金供給量を調整する政策。"},
    {"term": "財政政策", "definition": "政府が歳出・歳入を通じて景気に働きかける政策。"},
    {"term": "政策金利", "definition": "中央銀行が誘導目標とする短期金利。"},
    {"term": "為替介入", "definition": "通貨当局が外国為替市場で自国通貨を売買し、為替レートに影響を与える行為。"},
    {"term": "貿易収支", "definition": "財の輸出額から輸入額を差し引いた差額。"},
    {"term": "経常収支", "definition": "貿易収支に加え、サービス収支・所得収支などを含めた対外取引の総合収支。"},
    {"term": "イールドカーブ（利回り曲線）", "definition": "短期金利と長期金利の差を示す曲線。逆転（逆イールド）は景気後退の先行指標とされる。"},
    {"term": "量的緩和（QE）", "definition": "中央銀行が国債などを大量に買い入れ、市場に資金を供給する金融政策。"},
    {"term": "インフレターゲット", "definition": "中央銀行が目標とする物価上昇率を明示し、それに沿って金融政策を運営する枠組み。"},
    {"term": "有効求人倍率", "definition": "求職者1人当たりの求人数を示す指標。労働市場の需給を表す。"},
    {"term": "消費者物価指数（CPI）", "definition": "家計が購入する財・サービスの価格変動を示す指数。"},
    {"term": "失業率", "definition": "労働力人口に占める失業者の割合。"},
    {"term": "PMI（購買担当者景気指数）", "definition": "製造業・サービス業の購買担当者への調査をもとに算出する景気動向指数。50が拡大・縮小の分岐点。"},
    {"term": "信用格付け", "definition": "格付け機関が国や企業の債務履行能力を評価したもの。"},
    {"term": "ソブリンリスク", "definition": "国家が対外債務を履行できなくなるリスク。"},
    {"term": "スタグフレーション", "definition": "景気停滞（スタグネーション）と物価上昇（インフレーション）が同時に起こる状態。"},
    {"term": "リセッション（景気後退）", "definition": "経済活動が広範囲かつ持続的に縮小する状態。一般に実質GDPが2四半期連続でマイナス成長になることを指す。"},
]


def pick_term_of_day(today=None):
    """日替わりで固定リストから経済用語を1つ選ぶ (Claude API不使用、決定論的)。"""
    today = today or _date.today()
    index = today.timetuple().tm_yday % len(ECONOMIC_TERMS)
    return ECONOMIC_TERMS[index]
