"""summary.json (STEP2の出力) を、Obsidianで読む「新聞面」Markdownに整形する。

スマホのObsidianで読みやすいよう、見出しレベルは 紙名(#) / 面(##) / 1面記事(###) の3段に抑え、
表や callout などの装飾は使わない。
"""

from datetime import date
from urllib.parse import quote

WEEKDAYS_JA = "月火水木金土日"
NO_SUMMARY_TEXT = "要約なし（本文未取得のため）"


def _source_link(item):
    suffix = "（英語記事）" if item.get("lang") == "en" else ""
    return f"[{item['source']}]({item['url']}){suffix}"


def _front_page_article(number, item):
    return [
        f"### {number}. {item['headline']}",
        "",
        item["summary"] or NO_SUMMARY_TEXT,
        "",
        f"出典: {_source_link(item)}",
        "",
    ]


def _section_article(item):
    lines = [f"- **{item['headline']}**"]
    if item["summary"]:
        lines.append(f"  {item['summary']}")
    lines.append(f"  {_source_link(item)}")
    return lines


def render_newspaper(digest, config):
    labels = config.get("category_labels", {})
    paper_title = config.get("obsidian", {}).get("paper_title", "朝刊ダイジェスト")
    day = date.fromisoformat(digest["date"])

    lines = [
        f"# {paper_title}",
        "",
        f"**{day.year}年{day.month}月{day.day}日（{WEEKDAYS_JA[day.weekday()]}）**",
        "",
        "## 今日の1面",
        "",
    ]
    for number, item in enumerate(digest["front_page"], start=1):
        lines.extend(_front_page_article(number, item))

    for key in config.get("category_order", []):
        lines.extend(["---", "", f"## {labels.get(key, key)}", ""])
        items = digest["sections"].get(key) or []
        if not items:
            lines.extend(["本日の掲載はありません。", ""])
            continue
        for item in items:
            lines.extend(_section_article(item))
            lines.append("")

    keyword = digest.get("keyword")
    if keyword:
        lines.extend(["---", "", "## 今日の言葉", "", f"**{keyword['term']}**", "", keyword["explanation"], ""])

    return "\n".join(lines)


def note_path(config, day):
    """vault内でのノートのパス (拡張子なし)。例: daily/2026-11-01"""
    obsidian_config = config.get("obsidian", {})
    note_name = day.strftime(obsidian_config.get("filename_format", "%Y-%m-%d.md")).removesuffix(".md")
    folder = obsidian_config.get("note_folder", "").strip("/")
    return f"{folder}/{note_name}" if folder else note_name


def obsidian_uri(config, day):
    """obsidian://open のURIを返す。vault_name が未設定なら None。"""
    vault_name = config.get("obsidian", {}).get("vault_name")
    if not vault_name:
        return None
    return f"obsidian://open?vault={quote(vault_name, safe='')}&file={quote(note_path(config, day), safe='')}"
