"""STEP2: articles.json + prompts/summarize.md を `claude -p` に1回だけ渡し、
summary.json (今日の1面・カテゴリ面の構造化データ) を生成する。

Anthropic APIキーは使用しない。Claude Code の headless モード（`claude -p`）を
サブプロセスとして呼び出すことでAI処理を行う（Claude Proサブスクリプションの
認証をそのまま利用する想定）。

Markdownへの整形 (新聞面) とSlack通知の組み立ては STEP3 (distribute.py) が行う。
"""

import html
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from config_loader import (
    ARTICLES_JSON_PATH,
    DATA_DIR,
    PROJECT_ROOT,
    PROMPTS_DIR,
    SUMMARY_JSON_PATH,
    load_config,
)

WORK_DIR = PROJECT_ROOT / ".claude_work"

_TAG_RE = re.compile(r"<[^>]+>")
_SPACE_RE = re.compile(r"\s+")

# 見出し・要約に株価指数の数値が入っていないかの簡易チェック (警告のみ。除去はしない)
_INDEX_NUMBER_RE = re.compile(
    r"(日経平均|日経225|TOPIX|ダウ|NYダウ|S&P\s?500|ナスダック|Nasdaq|Dow)[^。、]{0,12}?[0-9０-９][0-9０-９,，.．]*\s*(円|ドル|ポイント|pt|%|％)"
)


def _plain_description(article):
    """descriptionのHTML (Google Newsはリンクタグ入り) を平文にし、見出しの繰り返しなら空にする。

    プロンプトを小さくするためだけの整形で、articles.json 自体は変更しない。
    """
    text = _SPACE_RE.sub(" ", html.unescape(_TAG_RE.sub(" ", article.get("description", "")))).strip()
    title = article.get("title", "")
    if not text or text in title or title.startswith(text):
        return ""
    return text


def build_prompt(articles, config):
    template = (PROMPTS_DIR / "summarize.md").read_text(encoding="utf-8")
    today_str = datetime.now(ZoneInfo("Asia/Tokyo")).strftime("%Y-%m-%d")
    labels = config.get("category_labels", {})
    category_lines = "\n".join(
        f"- `{key}`: {labels.get(key, key)}" for key in config.get("category_order", [])
    )
    prompt_articles = [
        {
            "title": a["title"],
            "url": a["url"],
            "source": a["source"],
            "published": a.get("published", ""),
            "description": _plain_description(a),
            "category_hint": a.get("category_hint", ""),
            "lang": a.get("lang", "ja"),
        }
        for a in articles
    ]
    articles_json = json.dumps(prompt_articles, ensure_ascii=False, separators=(",", ":"))
    return (
        f"{template}\n\n"
        "## カテゴリ一覧（キー: 表示名）\n\n"
        f"{category_lines}\n\n"
        f"本日の日付は {today_str} です。\n\n"
        "---\n\n"
        "以下が本日取得した記事一覧（JSON）です。この情報の範囲内でのみ作業してください:\n\n"
        f"```json\n{articles_json}\n```\n"
    )


def parse_digest_json(text):
    """claude -p の出力からJSONオブジェクトを取り出す (コードフェンスや前後の文が付いていても許容)。"""
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("出力にJSONオブジェクトが見つかりません")
    return json.loads(text[start:end + 1])


def _clean_item(item, articles_by_url, warnings, where):
    """1記事分を検証・正規化する。入力記事に無いURLの記事は捨てる (原文URLの保証)。"""
    if not isinstance(item, dict):
        warnings.append(f"{where}: 記事がオブジェクトでないため破棄")
        return None
    url = (item.get("url") or "").strip()
    headline = (item.get("headline") or "").strip()
    if url not in articles_by_url:
        warnings.append(f"{where}: 入力に無いURLのため破棄: {headline} ({url})")
        return None
    if not headline:
        warnings.append(f"{where}: 見出しが空のため破棄: {url}")
        return None
    summary = item.get("summary")
    summary = summary.strip() if isinstance(summary, str) and summary.strip() else None
    source_article = articles_by_url[url]
    for text in (headline, summary or ""):
        if _INDEX_NUMBER_RE.search(text):
            warnings.append(f"{where}: 株価指数の数値らしき表記があります: {text}")
    return {
        "headline": headline,
        "summary": summary,
        "source": (item.get("source") or "").strip() or source_article["source"],
        "url": url,
        "lang": source_article.get("lang", "ja"),
        "category": item.get("category"),
    }


def validate_digest(raw, articles, config):
    """構造を検証し、配信に使える形に正規化する。致命的な不備は ValueError。"""
    if not isinstance(raw, dict):
        raise ValueError("トップレベルがJSONオブジェクトではありません")

    articles_by_url = {a["url"]: a for a in articles}
    category_order = config.get("category_order", [])
    warnings = []

    front_page = []
    used_urls = set()
    for i, item in enumerate(raw.get("front_page") or []):
        cleaned = _clean_item(item, articles_by_url, warnings, f"1面[{i}]")
        if cleaned and cleaned["url"] not in used_urls:
            used_urls.add(cleaned["url"])
            front_page.append(cleaned)
    if not front_page:
        raise ValueError("今日の1面 (front_page) に有効な記事が1件もありません")

    raw_sections = raw.get("sections") or {}
    if not isinstance(raw_sections, dict):
        raise ValueError("sections がオブジェクトではありません")
    unknown = set(raw_sections) - set(category_order)
    if unknown:
        warnings.append(f"未知のカテゴリキーを無視: {sorted(unknown)}")

    sections = {}
    for key in category_order:
        items = []
        for i, item in enumerate(raw_sections.get(key) or []):
            cleaned = _clean_item(item, articles_by_url, warnings, f"{key}[{i}]")
            if cleaned and cleaned["url"] not in used_urls:  # 1面との重複・面同士の重複は載せない
                used_urls.add(cleaned["url"])
                cleaned["category"] = key
                items.append(cleaned)
        sections[key] = items

    keyword = raw.get("keyword")
    if not (isinstance(keyword, dict) and keyword.get("term") and keyword.get("explanation")):
        keyword = None

    digest = {
        "date": datetime.now(ZoneInfo("Asia/Tokyo")).strftime("%Y-%m-%d"),
        "front_page": front_page,
        "sections": sections,
        "keyword": keyword,
    }
    return digest, warnings


def run_claude(prompt_text, claude_config):
    cli_path = claude_config.get("cli_path", "claude")
    if shutil.which(cli_path) is None and not Path(cli_path).exists():
        raise RuntimeError(
            f"claude コマンドが見つかりません ({cli_path})。config.yaml の claude.cli_path を確認してください。"
        )

    WORK_DIR.mkdir(parents=True, exist_ok=True)

    # プロンプト本文はコマンドライン引数ではなく stdin で渡す
    # (Windowsはコマンドライン長が約32,000文字に制限されており、記事JSONを引数に入れると
    #  WinError 206 で起動自体に失敗するため)。
    cmd = [
        cli_path,
        "-p",
        "--model", claude_config.get("model", "sonnet"),
        "--output-format", "json",
        "--tools", "",  # ツール一切不要（テキスト生成のみ）→ 権限確認ダイアログが原理的に発生しない
        "--permission-mode", claude_config.get("permission_mode", "dontAsk"),
        "--no-session-persistence",  # セッション保存を無効化 → 再開ダイアログの発生源を断つ
        "--max-budget-usd", str(claude_config.get("max_budget_usd", 2.0)),
    ]

    timeout_seconds = claude_config.get("timeout_seconds", 600)
    try:
        result = subprocess.run(
            cmd,
            input=prompt_text,
            cwd=WORK_DIR,  # 既存プロジェクトと分離した専用ディレクトリで実行 (CLAUDE.md等を読ませない)
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"claude -p がタイムアウトしました ({timeout_seconds}秒)") from exc

    if result.returncode != 0:
        raise RuntimeError(
            f"claude -p が終了コード {result.returncode} で失敗しました。\n"
            f"stderr: {result.stderr[-2000:]}"
        )

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"claude -p の出力をJSONとして解釈できませんでした: {exc}\n"
            f"stdout先頭500文字: {result.stdout[:500]}"
        ) from exc

    if payload.get("is_error"):
        raise RuntimeError(f"claude -p がエラーを返しました: {payload}")

    text = payload.get("result", "")
    if not text.strip():
        raise RuntimeError("claude -p の出力が空でした。")

    return text


def main():
    config = load_config()

    if not ARTICLES_JSON_PATH.exists():
        print(f"[ERROR] {ARTICLES_JSON_PATH} が見つかりません。先に fetch_rss.py を実行してください。", file=sys.stderr)
        sys.exit(1)

    with open(ARTICLES_JSON_PATH, encoding="utf-8") as f:
        articles = json.load(f)

    if not articles:
        print("[WARN] articles.json が空です。要約対象がないため summary.json は生成しません。", file=sys.stderr)
        sys.exit(1)

    prompt_text = build_prompt(articles, config)

    try:
        output_text = run_claude(prompt_text, config.get("claude", {}))
    except RuntimeError as exc:
        print(f"[ERROR] STEP2 (claude -p 呼び出し) に失敗しました: {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        digest, warnings = validate_digest(parse_digest_json(output_text), articles, config)
    except ValueError as exc:  # json.JSONDecodeError も ValueError のサブクラス
        WORK_DIR.mkdir(parents=True, exist_ok=True)
        (WORK_DIR / "last_invalid_output.txt").write_text(output_text, encoding="utf-8")
        print(
            f"[ERROR] 生成された出力の構造が不正です: {exc}。"
            " 壊れたデータを配信しないため summary.json は書き込みません。"
            f" (出力は {WORK_DIR / 'last_invalid_output.txt'} に保存)",
            file=sys.stderr,
        )
        sys.exit(1)

    for warning in warnings:
        print(f"[WARN] {warning}", file=sys.stderr)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(SUMMARY_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(digest, f, ensure_ascii=False, indent=2)

    section_counts = ", ".join(f"{k}={len(v)}" for k, v in digest["sections"].items())
    print(
        f"[INFO] {len(articles)}件の記事から summary.json を生成しました "
        f"(1面={len(digest['front_page'])}, {section_counts})。"
    )


if __name__ == "__main__":
    main()
