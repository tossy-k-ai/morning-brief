"""RSS生存確認スクリプト。

インターネットに実際にアクセスできる環境（ローカル、または GitHub Actions の
workflow_dispatch / cron 実行）で実行し、sources.py の候補URLが

  1. HTTP 200 を返すか
  2. XML/RSSとしてパースできるか
  3. title / link / published / summary が取れるか

を確認する。--discover を付けると、DISCOVERY_PAGES のHTMLから
<link type="application/rss+xml"> やRSS/RDFファイルへのリンクも自動探索して
同様にテストする。

使い方:
    python check_feeds.py
    python check_feeds.py --discover

生きているRSSが1件も見つからない場合は終了コード1を返す。
その場合は sources.py を書き換えず、ユーザーに報告すること。
"""

import re
import sys
import urllib.parse

import feedparser
import requests

from sources import DISCOVERY_PAGES, SOURCES

TIMEOUT = 10
USER_AGENT = "morning-brief-digest/1.0 (+https://github.com/tossy-k-ai/morning-brief)"

LINK_TAG_RE = re.compile(
    r'<link[^>]+type=["\']application/(?:rss|rdf)\+xml["\'][^>]*>', re.IGNORECASE
)
HREF_RE = re.compile(r'href=["\']([^"\']+)["\']', re.IGNORECASE)
XML_HREF_RE = re.compile(r'href=["\']([^"\']+\.(?:xml|rdf))["\']', re.IGNORECASE)


def check_url(name, url):
    print(f"--- {name}: {url}")
    try:
        resp = requests.get(url, timeout=TIMEOUT, headers={"User-Agent": USER_AGENT})
    except requests.RequestException as exc:
        print(f"    [NG] リクエスト失敗: {exc}")
        return False

    print(f"    HTTP {resp.status_code}")
    if resp.status_code != 200:
        print("    [NG] ステータスが200以外")
        return False

    parsed = feedparser.parse(resp.content)
    if parsed.bozo and not parsed.entries:
        print(f"    [NG] XML/RSSとしてパース不可: {parsed.bozo_exception}")
        return False
    if not parsed.entries:
        print("    [NG] エントリが0件")
        return False

    entry = parsed.entries[0]
    has_title = bool(entry.get("title"))
    has_link = bool(entry.get("link"))
    has_published = bool(entry.get("published"))
    has_summary = bool(entry.get("summary"))
    print(
        f"    [OK] entries={len(parsed.entries)} "
        f"title={has_title} link={has_link} published={has_published} summary={has_summary}"
    )
    print(f"    例: {entry.get('title')!r} -> {entry.get('link')!r}")
    return True


def discover_feed_urls(page_url):
    try:
        resp = requests.get(page_url, timeout=TIMEOUT, headers={"User-Agent": USER_AGENT})
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"  [NG] ページ取得失敗 {page_url}: {exc}")
        return []

    html = resp.text
    found = set()
    for tag in LINK_TAG_RE.findall(html):
        m = HREF_RE.search(tag)
        if m:
            found.add(urllib.parse.urljoin(page_url, m.group(1)))
    for href in XML_HREF_RE.findall(html):
        found.add(urllib.parse.urljoin(page_url, href))
    return sorted(found)


def main():
    discover = "--discover" in sys.argv
    working = []

    print("=== 候補URL確認 (sources.py の SOURCES) ===")
    for source in SOURCES:
        if check_url(source.name, source.url):
            working.append((source.name, source.url))

    if discover:
        print("\n=== ページからのRSS/RDFリンク自動発見 (DISCOVERY_PAGES) ===")
        for page in DISCOVERY_PAGES:
            print(f"[探索] {page}")
            for feed_url in discover_feed_urls(page):
                if check_url(f"discovered@{page}", feed_url):
                    working.append((f"discovered@{page}", feed_url))

    print("\n=== 結果 ===")
    if not working:
        print("[NG] 生きているRSSが1件も見つかりませんでした。")
        print("推測でURLを追加せず、ユーザーに報告してください。")
        sys.exit(1)

    for name, url in working:
        print(f"[OK] {name}: {url}")
    sys.exit(0)


if __name__ == "__main__":
    main()
