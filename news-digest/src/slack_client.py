"""Slack投稿: 今日の1面の見出し一覧を短い通知としてWebhook投稿する。

全文はObsidianのdailyノート (新聞面) に置き、Slackには見出しだけを流す。
Webhook投稿・50ブロック分割・エラー通知のロジックは
../morning-brief (main.py / slack_formatter.py) で実績のあるものを流用している。
このプロジェクト単体で動くよう、依存を持ち込まず自己完結させてある。
"""

import json
import urllib.error
import urllib.request

MAX_BLOCKS_PER_MESSAGE = 50
REQUEST_TIMEOUT = 15


def _escape_mrkdwn(text):
    """Slack mrkdwn の制御文字 (&, <, >) をエスケープする。"""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_headline_blocks(digest, max_headlines=8, obsidian_uri=None, note_label=None):
    """日付 + 1面の見出し一覧 + Obsidianへの案内 のブロックを作る。"""
    headlines = "\n".join(
        f"• <{item['url']}|{_escape_mrkdwn(item['headline'])}>"
        for item in digest["front_page"][:max_headlines]
    )
    guide = "全文はObsidianのdailyノートへ"
    if note_label:
        guide += f"（{_escape_mrkdwn(note_label)}）"
    if obsidian_uri:
        guide += f"\n<{obsidian_uri}|Obsidianで開く>"
    return [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"🗞 今日の1面 {digest['date']}", "emoji": True},
        },
        {"type": "section", "text": {"type": "mrkdwn", "text": headlines}},
        {"type": "context", "elements": [{"type": "mrkdwn", "text": guide}]},
    ]


def chunk_blocks(blocks, max_blocks=MAX_BLOCKS_PER_MESSAGE):
    """1メッセージが50ブロックを超えないよう分割する。"""
    return [blocks[i:i + max_blocks] for i in range(0, len(blocks), max_blocks)]


def post_to_slack(webhook_url, blocks, text_fallback):
    payload = json.dumps({"blocks": blocks, "text": text_fallback}).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            body = resp.read().decode("utf-8")
            if resp.status != 200:
                raise RuntimeError(f"Slack webhook returned HTTP {resp.status}: {body}")
    except urllib.error.HTTPError as exc:
        raise RuntimeError(
            f"Slack webhook returned HTTP {exc.code}: {exc.read().decode('utf-8', 'ignore')}"
        ) from exc


def post_message_in_chunks(webhook_url, blocks, text_fallback="Daily News"):
    for chunk in chunk_blocks(blocks):
        post_to_slack(webhook_url, chunk, text_fallback)


def post_error(webhook_url, message):
    """失敗時にSlackへエラー内容を投稿する（可能な限り）。投稿自体が失敗してもFalseを返すだけで例外は投げない。"""
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "🚨 news-digest 配信エラー", "emoji": True},
        },
        {"type": "section", "text": {"type": "mrkdwn", "text": message}},
    ]
    try:
        post_to_slack(webhook_url, blocks, text_fallback="news-digest 配信エラー")
        return True
    except Exception:
        return False
