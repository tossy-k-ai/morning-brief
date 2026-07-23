"""STEP2: articles.json + prompts/summarize.md を `claude -p` に1回だけ渡し、
summary.md を生成する。

Anthropic APIキーは使用しない。Claude Code の headless モード（`claude -p`）を
サブプロセスとして呼び出すことでAI処理を行う（Claude Proサブスクリプションの
認証をそのまま利用する想定）。
"""

import json
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
    SUMMARY_MD_PATH,
    load_config,
)

WORK_DIR = PROJECT_ROOT / ".claude_work"

REQUIRED_HEADINGS = ["# Daily News", "## ⭐ 今日最重要", "## 📖 今日覚える言葉"]


def build_prompt(articles):
    template = (PROMPTS_DIR / "summarize.md").read_text(encoding="utf-8")
    today_str = datetime.now(ZoneInfo("Asia/Tokyo")).strftime("%Y-%m-%d")
    articles_json = json.dumps(articles, ensure_ascii=False, indent=2)
    return (
        f"{template}\n\n"
        f"本日の日付は {today_str} です。タイトルの `YYYY-MM-DD` はこれに置き換えてください。\n\n"
        "---\n\n"
        "以下が本日取得した記事一覧（JSON）です。この情報の範囲内でのみ作業してください:\n\n"
        f"```json\n{articles_json}\n```\n"
    )


def validate_structure(markdown_text):
    missing = [h for h in REQUIRED_HEADINGS if h not in markdown_text]
    return missing


def run_claude(prompt_text, claude_config):
    cli_path = claude_config.get("cli_path", "claude")
    if shutil.which(cli_path) is None and not Path(cli_path).exists():
        raise RuntimeError(
            f"claude コマンドが見つかりません ({cli_path})。config.yaml の claude.cli_path を確認してください。"
        )

    WORK_DIR.mkdir(parents=True, exist_ok=True)

    cmd = [
        cli_path,
        "-p", prompt_text,
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
        print("[WARN] articles.json が空です。要約対象がないため summary.md は生成しません。", file=sys.stderr)
        sys.exit(1)

    prompt_text = build_prompt(articles)

    try:
        markdown_text = run_claude(prompt_text, config.get("claude", {}))
    except RuntimeError as exc:
        print(f"[ERROR] STEP2 (claude -p 呼び出し) に失敗しました: {exc}", file=sys.stderr)
        sys.exit(1)

    missing = validate_structure(markdown_text)
    if missing:
        print(
            f"[ERROR] 生成されたMarkdownの構造が不正です（欠けている見出し: {missing}）。"
            " 壊れたファイルを配信しないため summary.md は書き込みません。",
            file=sys.stderr,
        )
        sys.exit(1)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(SUMMARY_MD_PATH, "w", encoding="utf-8") as f:
        f.write(markdown_text)

    print(f"[INFO] {len(articles)}件の記事から summary.md を生成しました。")


if __name__ == "__main__":
    main()
