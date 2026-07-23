"""RSS生存確認スクリプト（news-digest用）。

インターネットに実際にアクセスできる環境で実行し、config.yaml の候補URLが

  1. HTTP 200 を返すか
  2. XML/RSSとしてパースできるか
  3. title / link / published / description が取れるか
  4. (Google Newsの場合) リンクが実際の記事URLに解決できるか

を確認する。

使い方:
    python check_feeds.py

生きているRSSが1件も見つからない場合は終了コード1を返す。
その場合は config.yaml を書き換えず、ユーザーに報告すること。
"""

import sys
from urllib.parse import urlparse

import feedparser
import requests

from src.config_loader import load_config

TIMEOUT = 10
USER_AGENT = "news-digest/1.0"
GOOGLE_NEWS_HOST = "news.google.com"


def check_source(source):
    name = source["name"]
    url = source["url"]
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
    link = entry.get("link", "")
    has_title = bool(entry.get("title"))
    has_link = bool(link)
    has_published = bool(entry.get("published"))
    has_description = bool(entry.get("summary"))
    print(
        f"    [OK] entries={len(parsed.entries)} "
        f"title={has_title} link={has_link} published={has_published} description={has_description}"
    )
    print(f"    例: {entry.get('title')!r} -> {link!r}")

    if link and urlparse(link).netloc == GOOGLE_NEWS_HOST:
        resolved = resolve_link(link)
        if resolved != link:
            print(f"    [OK] Google Newsリンクの解決に成功: {resolved!r}")
        else:
            print("    [NG] Google Newsリンクを実記事URLに解決できませんでした（リダイレクト追跡失敗）")

    return True


def resolve_link(url):
    try:
        resp = requests.head(url, timeout=TIMEOUT, allow_redirects=True, headers={"User-Agent": USER_AGENT})
        if resp.url and urlparse(resp.url).netloc != GOOGLE_NEWS_HOST:
            return resp.url
    except requests.RequestException:
        pass

    try:
        resp = requests.get(
            url, timeout=TIMEOUT, allow_redirects=True, headers={"User-Agent": USER_AGENT}, stream=True
        )
        resp.close()
        if resp.url and urlparse(resp.url).netloc != GOOGLE_NEWS_HOST:
            return resp.url
    except requests.RequestException:
        pass

    return url


def main():
    config = load_config()
    sources = config.get("sources", [])

    working = []
    for source in sources:
        if check_source(source):
            working.append(source["name"])

    print("\n=== 結果 ===")
    if not working:
        print("[NG] 生きているRSSが1件も見つかりませんでした。")
        print("推測でURLを追加せず、ユーザーに報告してください。")
        sys.exit(1)

    for name in working:
        print(f"[OK] {name}")
    sys.exit(0)


if __name__ == "__main__":
    main()
