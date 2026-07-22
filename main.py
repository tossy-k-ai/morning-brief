"""毎朝ニュース見出しダイジェスト — 収集〜整形〜配信〜失敗通知。

Claude APIは使用しない。見出しとリンクの配信のみを行う（要約はしない）。
"""

import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import feedparser
import requests

from slack_formatter import build_message_blocks, post_error, post_message_in_chunks
from sources import SOURCES

REQUEST_TIMEOUT = 10
MAX_ITEMS_PER_SOURCE = 8
USER_AGENT = "morning-brief-digest/1.0 (+https://github.com/tossy-k-ai/morning-brief)"


def fetch_source(source):
    """1ソース分のRSSを取得しパースする。失敗しても例外を投げず空リストを返す（フォールバック）。"""
    try:
        resp = requests.get(source.url, timeout=REQUEST_TIMEOUT, headers={"User-Agent": USER_AGENT})
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"[WARN] {source.name} ({source.url}) の取得に失敗: {exc}", file=sys.stderr)
        return []

    parsed = feedparser.parse(resp.content)
    if parsed.bozo and not parsed.entries:
        print(f"[WARN] {source.name} ({source.url}) のパースに失敗: {parsed.bozo_exception}", file=sys.stderr)
        return []

    articles = []
    for entry in parsed.entries[:MAX_ITEMS_PER_SOURCE]:
        link = entry.get("link", "")
        if not link:
            continue
        articles.append({
            "title": entry.get("title", "(タイトルなし)"),
            "link": link,
            "published": entry.get("published", ""),
            "summary": entry.get("summary", "").strip(),
        })
    return articles


def collect_all():
    """全ソースを取得し、リンクURL一致で重複除外する。1ソース失敗しても他は継続する。"""
    articles_by_source = {}
    seen_links = set()
    any_success = False

    for source in SOURCES:
        items = fetch_source(source)
        if items:
            any_success = True
        deduped = []
        for item in items:
            if item["link"] in seen_links:
                continue
            seen_links.add(item["link"])
            deduped.append(item)
        articles_by_source[source.name] = deduped

    return articles_by_source, any_success


def main():
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook_url:
        print("[ERROR] SLACK_WEBHOOK_URL が設定されていません。", file=sys.stderr)
        sys.exit(1)

    date_str = datetime.now(ZoneInfo("Asia/Tokyo")).strftime("%Y-%m-%d (%a)")

    articles_by_source, any_success = collect_all()
    total = sum(len(v) for v in articles_by_source.values())

    if not any_success:
        message = (
            f"{date_str} のニュース収集に失敗しました。全てのRSSソースが取得できませんでした。\n"
            "sources.py のURLが生きているか `python check_feeds.py --discover` で確認してください。"
        )
        print(f"[ERROR] {message}", file=sys.stderr)
        post_error(webhook_url, message)
        sys.exit(1)

    blocks = build_message_blocks(articles_by_source, date_str, total)
    try:
        post_message_in_chunks(webhook_url, blocks)
    except Exception as exc:
        print(f"[ERROR] Slackへの投稿に失敗: {exc}", file=sys.stderr)
        post_error(webhook_url, f"{date_str} のSlack投稿に失敗しました: {exc}")
        sys.exit(1)

    print(f"[INFO] {date_str}: 新着 {total} 件を配信しました。")


if __name__ == "__main__":
    main()
