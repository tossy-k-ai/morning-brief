"""STEP1: RSS取得 → articles.json 書き出し。

Claude APIは使用しない。ここでは記事の収集・鮮度フィルタ・重複除去のみを行う
（要約はSTEP2で claude -p が行う）。
"""

import calendar
import json
import sys
import time
from datetime import datetime, timezone
from urllib.parse import urlparse

import feedparser
import requests

from config_loader import ARTICLES_JSON_PATH, DATA_DIR, load_config
from dedupe import dedupe_articles

REQUEST_TIMEOUT = 10
REDIRECT_RESOLVE_TIMEOUT = 8
USER_AGENT = "news-digest/1.0"
GOOGLE_NEWS_HOST = "news.google.com"


def fetch_source(source):
    """1ソース分のRSSを取得しパースする。失敗しても例外を投げず空リストを返す（フォールバック）。"""
    name = source["name"]
    url = source["url"]
    max_items = source.get("max_items", 10)

    try:
        resp = requests.get(url, timeout=REQUEST_TIMEOUT, headers={"User-Agent": USER_AGENT})
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"[WARN] {name} ({url}) の取得に失敗: {exc}", file=sys.stderr)
        return []

    parsed = feedparser.parse(resp.content)
    if parsed.bozo and not parsed.entries:
        print(f"[WARN] {name} ({url}) のパースに失敗: {parsed.bozo_exception}", file=sys.stderr)
        return []

    articles = []
    for entry in parsed.entries[:max_items]:
        link = entry.get("link", "")
        if not link:
            continue
        articles.append({
            "title": entry.get("title", "(タイトルなし)"),
            "url": link,
            "source": name,
            "published": entry.get("published", ""),
            "published_parsed": entry.get("published_parsed"),
            "description": (entry.get("summary", "") or "").strip(),
            "category_hint": source.get("category", ""),
        })
    return articles


def is_fresh(article, max_age_hours):
    """published_parsedが無い記事は判定不能なので除外せず残す（取りこぼし防止）。"""
    struct = article.get("published_parsed")
    if not struct:
        return True
    published_utc = datetime.fromtimestamp(calendar.timegm(struct), tz=timezone.utc)
    age_hours = (datetime.now(timezone.utc) - published_utc).total_seconds() / 3600
    return age_hours <= max_age_hours


def resolve_google_news_link(url):
    """Google NewsのリダイレクトURLを実際の記事URLに解決する。解決できなければ元のURLを返す。"""
    if urlparse(url).netloc != GOOGLE_NEWS_HOST:
        return url
    try:
        resp = requests.head(
            url, timeout=REDIRECT_RESOLVE_TIMEOUT, allow_redirects=True, headers={"User-Agent": USER_AGENT}
        )
        if resp.url and urlparse(resp.url).netloc != GOOGLE_NEWS_HOST:
            return resp.url
    except requests.RequestException:
        pass

    try:
        resp = requests.get(
            url, timeout=REDIRECT_RESOLVE_TIMEOUT, allow_redirects=True,
            headers={"User-Agent": USER_AGENT}, stream=True,
        )
        resp.close()
        if resp.url and urlparse(resp.url).netloc != GOOGLE_NEWS_HOST:
            return resp.url
    except requests.RequestException as exc:
        print(f"[WARN] Google Newsリンクの解決に失敗、元のURLを使用: {url} ({exc})", file=sys.stderr)

    return url


def main():
    config = load_config()
    sources = [s for s in config.get("sources", []) if s.get("enabled", True)]
    max_age_hours = config.get("freshness", {}).get("max_age_hours", 24)
    title_similarity_threshold = config.get("dedupe", {}).get("title_similarity_threshold", 0.85)

    all_articles = []
    any_success = False

    for source in sources:
        items = fetch_source(source)
        if items:
            any_success = True
        all_articles.extend(items)

    fresh_articles = [a for a in all_articles if is_fresh(a, max_age_hours)]

    for article in fresh_articles:
        article["url"] = resolve_google_news_link(article["url"])
        article.pop("published_parsed", None)  # JSON化できないstruct_timeを削除

    deduped = dedupe_articles(fresh_articles, title_similarity_threshold)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(ARTICLES_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(deduped, f, ensure_ascii=False, indent=2)

    print(
        f"[INFO] 取得 {len(all_articles)}件 → 鮮度フィルタ後 {len(fresh_articles)}件 "
        f"→ 重複除去後 {len(deduped)}件 を {ARTICLES_JSON_PATH} に保存しました。"
    )

    if not any_success:
        print("[ERROR] 全てのRSSソースが取得できませんでした。", file=sys.stderr)
        sys.exit(1)

    if not deduped:
        print("[WARN] 記事が0件です（全ソース失敗ではないが、鮮度フィルタ等で0件になった可能性）。", file=sys.stderr)


if __name__ == "__main__":
    main()
