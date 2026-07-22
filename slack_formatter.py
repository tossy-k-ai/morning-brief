"""Slack Block Kit への変換とWebhook投稿。要約・改変は行わない。"""

import json
import urllib.error
import urllib.request

MAX_BLOCKS_PER_MESSAGE = 50
REQUEST_TIMEOUT = 15
GUIDANCE_TEXT = (
    "要約が欲しい記事はリンクを開き、スクリーンショットをClaude.aiのチャットに"
    "貼って要約を依頼してください。"
)


def build_message_blocks(articles_by_source, date_str, total_count):
    """記事データをSlack Block Kitのblocks配列に変換する（見出し・リンクのみ、要約なし）。"""
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"📰 本日のニュース見出し ({date_str})", "emoji": True},
        },
        {
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": f"本日は新着 {total_count} 件です。"}],
        },
        {"type": "divider"},
    ]

    for source_name, articles in articles_by_source.items():
        if not articles:
            continue
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*{source_name}*"},
        })
        for article in articles:
            text = f"• <{article['link']}|{article['title']}>"
            if article.get("summary"):
                text += f"\n{article['summary']}"
            blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": text}})
        blocks.append({"type": "divider"})

    blocks.append({
        "type": "context",
        "elements": [{"type": "mrkdwn", "text": GUIDANCE_TEXT}],
    })
    return blocks


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
        raise RuntimeError(f"Slack webhook returned HTTP {exc.code}: {exc.read().decode('utf-8', 'ignore')}") from exc


def post_message_in_chunks(webhook_url, blocks, text_fallback="本日のニュース見出し"):
    for chunk in chunk_blocks(blocks):
        post_to_slack(webhook_url, chunk, text_fallback)


def post_error(webhook_url, message):
    """失敗時にSlackへエラー内容を投稿する（可能な限り）。投稿自体が失敗してもFalseを返すだけで例外は投げない。"""
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "🚨 ニュースダイジェスト配信エラー", "emoji": True},
        },
        {"type": "section", "text": {"type": "mrkdwn", "text": message}},
    ]
    try:
        post_to_slack(webhook_url, blocks, text_fallback="ニュースダイジェスト配信エラー")
        return True
    except Exception:
        return False
