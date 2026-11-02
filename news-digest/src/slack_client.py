"""Slack投稿: 朝刊ダイジェストを全文形式 (要点 → カテゴリ別の見出しリンク＋1行要約) でWebhook投稿する。

体裁は朝ブリーフィングに合わせる: 先頭に日付と「今日の要点」、続いて *カテゴリ名* の太字見出しと
箇条書き (<URL|見出し> ＋ 次の行に1行要約)、末尾にObsidianノートへの案内。
1通に収まらない場合はカテゴリ単位で複数メッセージに分割する (項目は切り捨てない)。

Webhook投稿・エラー通知のロジックは ../morning-brief (main.py / slack_formatter.py) で
実績のあるものを流用している。このプロジェクト単体で動くよう、依存を持ち込まず自己完結させてある。
"""

import json
import urllib.error
import urllib.request
from datetime import date

from index_numbers import mask_index_numbers

REQUEST_TIMEOUT = 15

# 1通あたりの上限。Slackの仕様は 50ブロック/通、sectionのtextは3000文字まで。
# 文字数は仕様上の上限 (40,000文字で切り詰め) よりかなり手前で分け、スマホで「続きを読む」に
# 畳まれにくくする安全側の値にしている。
MAX_BLOCKS_PER_MESSAGE = 50
MAX_SECTION_CHARS = 3000
MAX_CHARS_PER_MESSAGE = 12000

WEEKDAYS_JA = "月火水木金土日"
FRONT_PAGE_LABEL = "今日の1面"
NO_SUMMARY_TEXT = "要約なし（本文未取得のため）"
KEY_POINT_HEADLINES = 3  # 「今日の要点」に並べる1面の見出し数


def _escape_mrkdwn(text):
    """Slack mrkdwn の制御文字 (&, <, >) をエスケープする。"""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _first_sentence(text):
    """1面の要約 (2〜3文) を1行に収めるため、最初の1文だけを返す。全文はObsidianにある。"""
    head, sep, _ = text.partition("。")
    return head + sep


class _Masker:
    """株価指数の数値を伏せ、伏せた箇所を記録する。"""

    def __init__(self):
        self.masked = []

    def __call__(self, text, where):
        result, changed = mask_index_numbers(text)
        if changed:
            self.masked.append(f"{where}: {text}")
        return result


def build_key_point(digest, mask):
    """「今日の要点」1行。1面の上位の見出しを機械的に並べる (要約ステップに専用の項目は無い)。"""
    headlines = [item["headline"] for item in digest["front_page"][:KEY_POINT_HEADLINES]]
    rest = len(digest["front_page"]) - len(headlines)
    line = "／".join(headlines)
    if rest > 0:
        line += f"　ほか{rest}本"
    return mask(line, "今日の要点")


def _item_lines(item, mask, where, one_sentence):
    headline = mask(item["headline"], f"{where} 見出し")
    source = item["source"] + ("・英語" if item.get("lang") == "en" else "")
    summary = item.get("summary")
    if summary:
        summary = mask(_first_sentence(summary) if one_sentence else summary, f"{where} 要約")
    else:
        summary = NO_SUMMARY_TEXT
    return (
        f"• <{item['url']}|{_escape_mrkdwn(headline)}>（{_escape_mrkdwn(source)}）\n"
        f"　{_escape_mrkdwn(summary)}"
    )


def _category_sections(label, entries):
    """1カテゴリ分を section ブロックにする。3000文字を超える場合は項目単位で複数sectionに分ける。"""
    title = f"*{_escape_mrkdwn(label)}*"
    if not entries:
        return [_section(f"{title}\n本日の掲載はありません。")]
    sections, current = [], title
    for entry in entries:
        if len(current) + 1 + len(entry) > MAX_SECTION_CHARS:
            sections.append(_section(current))
            current = f"{title}（続き）"
        current += "\n" + entry
    sections.append(_section(current))
    return sections


def _section(text):
    return {"type": "section", "text": {"type": "mrkdwn", "text": text}}


def _context(text):
    return {"type": "context", "elements": [{"type": "mrkdwn", "text": text}]}


def _block_chars(block):
    if block["type"] == "context":
        return sum(len(e["text"]) for e in block["elements"])
    if "text" in block:
        return len(block["text"]["text"])
    return 0


def _pack(units, reserve_blocks=1, reserve_chars=100):
    """ブロックのまとまり (units) を、上限内に収まるよう順に複数メッセージへ詰める。

    まとまり (= 1カテゴリ) は途中で切らない。1まとまりだけで上限を超える場合のみ、ブロック単位で分ける。
    続きメッセージの先頭に付ける表示のぶん (reserve_*) を空けておく。
    """
    max_blocks = MAX_BLOCKS_PER_MESSAGE - reserve_blocks
    max_chars = MAX_CHARS_PER_MESSAGE - reserve_chars
    messages, current, chars = [], [], 0
    for unit in units:
        unit_chars = sum(_block_chars(b) for b in unit)
        if current and (len(current) + len(unit) > max_blocks or chars + unit_chars > max_chars):
            messages.append(current)
            current, chars = [], 0
        if len(unit) > max_blocks or unit_chars > max_chars:  # 1カテゴリが単独で上限超え (通常は起きない)
            for block in unit:
                if current and (len(current) + 1 > max_blocks or chars + _block_chars(block) > max_chars):
                    messages.append(current)
                    current, chars = [], 0
                current.append(block)
                chars += _block_chars(block)
            continue
        current.extend(unit)
        chars += unit_chars
    if current:
        messages.append(current)
    return messages


def build_full_messages(digest, config, obsidian_uri=None, note_label=None, obsidian_saved=True):
    """全文形式のSlackメッセージ (ブロックのリストのリスト) を作る。

    戻り値: (messages, masked)。masked は株価指数の数値を伏せた箇所の一覧 (ログ用)。
    """
    labels = config.get("category_labels", {})
    paper_title = config.get("obsidian", {}).get("paper_title", "朝刊ダイジェスト")
    day = date.fromisoformat(digest["date"])
    date_label = f"{day.year}年{day.month}月{day.day}日（{WEEKDAYS_JA[day.weekday()]}）"
    mask = _Masker()

    head = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"🗞 {paper_title} {date_label}", "emoji": True},
        },
        _section(f"*今日の要点*　{_escape_mrkdwn(build_key_point(digest, mask))}"),
    ]

    categories = [(FRONT_PAGE_LABEL, digest["front_page"], True)]
    for key in config.get("category_order", []):
        categories.append((labels.get(key, key), digest["sections"].get(key) or [], False))

    units = [head]
    for label, items, is_front in categories:
        entries = [
            _item_lines(item, mask, f"{label}[{i}]", one_sentence=is_front)
            for i, item in enumerate(items)
        ]
        units.append([{"type": "divider"}] + _category_sections(label, entries))

    if obsidian_saved:
        guide = "全文（1面の詳しい要約・今日の言葉）はObsidianのdailyノートに保存しました"
    else:
        guide = "⚠ Obsidianのdailyノートへの保存に失敗しました（全文はこのSlack投稿のみ）"
    if note_label:
        guide += f"（{_escape_mrkdwn(note_label)}）"
    if obsidian_uri:
        guide += f"\n<{obsidian_uri}|Obsidianで開く>"
    units.append([{"type": "divider"}, _context(guide)])

    messages = _pack(units)
    total = len(messages)
    for number, blocks in enumerate(messages[1:], start=2):
        blocks.insert(0, _context(f"{paper_title} {date_label}（続き {number}/{total}）"))
    return messages, mask.masked


def blocks_to_text(blocks):
    """確認用: ブロックを人が読めるテキストにする (投稿はしない)。"""
    lines = []
    for block in blocks:
        if block["type"] == "divider":
            lines.append("----")
        elif block["type"] == "context":
            lines.extend(e["text"] for e in block["elements"])
        else:
            lines.append(block["text"]["text"])
    return "\n".join(lines)


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


def post_messages(webhook_url, messages, text_fallback="Daily News"):
    """メッセージを順に投稿する。途中で失敗した場合は、何通目まで送れたかを添えて例外を投げる。"""
    total = len(messages)
    for number, blocks in enumerate(messages, start=1):
        fallback = text_fallback if total == 1 else f"{text_fallback} ({number}/{total})"
        try:
            post_to_slack(webhook_url, blocks, fallback)
        except Exception as exc:
            raise RuntimeError(f"{total}通中{number}通目の投稿に失敗しました（{number - 1}通は投稿済み）: {exc}") from exc
    return total


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
