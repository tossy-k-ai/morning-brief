"""Slack投稿: summary.md (Markdown) をSlack Block Kitに変換してWebhook投稿する。

Webhook投稿・50ブロック分割・エラー通知のロジックは
../morning-brief (main.py / slack_formatter.py) で実績のあるものを流用している。
このプロジェクト単体で動くよう、依存を持ち込まず自己完結させてある。
"""

import json
import re
import urllib.error
import urllib.request

MAX_BLOCKS_PER_MESSAGE = 50
MAX_SECTION_TEXT_CHARS = 2900  # Slackのsection text上限3000文字に対する安全マージン
REQUEST_TIMEOUT = 15

_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def _convert_inline_markdown(line):
    """Markdownのインライン記法をSlack mrkdwnに変換する（太字・リンク）。"""
    line = _LINK_RE.sub(r"<\2|\1>", line)
    line = _BOLD_RE.sub(r"*\1*", line)
    return line


def _flush_section(buffer_lines, blocks):
    text = "\n".join(buffer_lines).strip()
    if not text:
        return
    for i in range(0, len(text), MAX_SECTION_TEXT_CHARS):
        chunk_text = text[i:i + MAX_SECTION_TEXT_CHARS]
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": chunk_text}})


def markdown_to_slack_blocks(markdown_text):
    """summary.md のMarkdownをSlack Block Kitのblocks配列に変換する。

    見出し構造 (# / ## / ### )・区切り線 (---) を前提にパースする。
    prompts/summarize.md で指定しているテンプレート構造に対応。
    """
    blocks = []
    buffer_lines = []

    for raw_line in markdown_text.splitlines():
        line = raw_line.rstrip()

        if line.startswith("# "):
            _flush_section(buffer_lines, blocks)
            buffer_lines = []
            blocks.append({
                "type": "header",
                "text": {"type": "plain_text", "text": line[2:].strip(), "emoji": True},
            })
        elif line.startswith("## ") or line.startswith("### "):
            _flush_section(buffer_lines, blocks)
            buffer_lines = []
            heading_text = line.lstrip("#").strip()
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*{_convert_inline_markdown(heading_text)}*"},
            })
        elif line.strip() == "---":
            _flush_section(buffer_lines, blocks)
            buffer_lines = []
            blocks.append({"type": "divider"})
        else:
            buffer_lines.append(_convert_inline_markdown(line))

    _flush_section(buffer_lines, blocks)
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
