"""STEP3: summary.json を読み込み、Obsidianへ新聞面を保存し、Slackへ全文形式で配信する。

どちらかが失敗しても、もう片方は独立して試みる（ベストエフォート）。

オプション:
  --slack-only  Slack配信だけを行う (Obsidianノート・data/summary.md は書き換えない)。配信の再実行用。
  --dry-run     Slackへは投稿せず、整形後の本文と通数・文字数を表示する。Obsidianにも書かない。
"""

import argparse
import json
import os
import sys
from datetime import date

from config_loader import DATA_DIR, SUMMARY_JSON_PATH, SUMMARY_MD_PATH, load_config, load_dotenv
from newspaper import note_path, obsidian_uri, render_newspaper
from obsidian_writer import write_daily_note
from slack_client import blocks_to_text, build_full_messages, post_error, post_messages


def build_slack_messages(digest, config, today, obsidian_saved=True):
    messages, masked = build_full_messages(
        digest,
        config,
        obsidian_uri=obsidian_uri(config, today),
        note_label=note_path(config, today),
        obsidian_saved=obsidian_saved,
    )
    for where in masked:
        print(f"[WARN] Slack本文の株価指数の数値を伏せました: {where}", file=sys.stderr)
    return messages


def distribute_to_slack(digest, config, today, obsidian_saved=True):
    slack_config = config.get("slack", {})
    webhook_env_var = slack_config.get("webhook_env_var", "SLACK_WEBHOOK_URL")
    webhook_url = os.environ.get(webhook_env_var)
    if not webhook_url:
        print(f"[ERROR] 環境変数 {webhook_env_var} が設定されていません。Slack配信をスキップします。", file=sys.stderr)
        return False, None

    try:
        messages = build_slack_messages(digest, config, today, obsidian_saved)
        total = post_messages(webhook_url, messages, text_fallback=f"朝刊ダイジェスト {digest['date']}")
        print(f"[INFO] Slackへの全文配信に成功しました（{total}通で投稿）。")
        return True, webhook_url
    except Exception as exc:
        print(f"[ERROR] Slackへの配信に失敗しました: {exc}", file=sys.stderr)
        return False, webhook_url


def distribute_to_obsidian(markdown_text, config, today):
    obsidian_config = config.get("obsidian", {})
    vault_path = obsidian_config.get("vault_path")
    if not vault_path:
        print("[ERROR] config.yaml に obsidian.vault_path が設定されていません。Obsidian保存をスキップします。", file=sys.stderr)
        return False

    try:
        file_path = write_daily_note(
            markdown_text,
            vault_path,
            filename_format=obsidian_config.get("filename_format", "%Y-%m-%d.md"),
            mode=obsidian_config.get("mode", "append"),
            today=today,
        )
        print(f"[INFO] Obsidian Vaultへの保存に成功しました: {file_path}")
        return True
    except Exception as exc:
        print(f"[ERROR] Obsidian Vaultへの保存に失敗しました: {exc}", file=sys.stderr)
        return False


def dry_run(digest, config, today):
    messages = build_slack_messages(digest, config, today)
    for number, blocks in enumerate(messages, start=1):
        text = blocks_to_text(blocks)
        print(f"===== Slack {number}/{len(messages)} 通目 ({len(blocks)}ブロック, {len(text)}文字) =====")
        print(text)
    print(f"[INFO] dry-run: {len(messages)}通で投稿する想定です（投稿はしていません）。")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--slack-only", action="store_true", help="Slack配信だけを行う (Obsidianは書き換えない)")
    parser.add_argument("--dry-run", action="store_true", help="投稿せずにSlack本文を表示する")
    args = parser.parse_args()

    load_dotenv()
    config = load_config()
    today = date.today()

    if not SUMMARY_JSON_PATH.exists():
        print(f"[ERROR] {SUMMARY_JSON_PATH} が見つかりません。先に generate_summary.py を実行してください。", file=sys.stderr)
        sys.exit(1)

    with open(SUMMARY_JSON_PATH, encoding="utf-8") as f:
        digest = json.load(f)

    # STEP2が失敗した日に前日の summary.json を再配信しないための確認
    if digest.get("date") != today.isoformat():
        print(
            f"[ERROR] summary.json の日付 ({digest.get('date')}) が本日 ({today.isoformat()}) と異なります。"
            " 古い内容を配信しないため中止します。generate_summary.py を再実行してください。",
            file=sys.stderr,
        )
        sys.exit(1)

    if args.dry_run:
        dry_run(digest, config, today)
        return

    if args.slack_only:
        slack_ok, webhook_url = distribute_to_slack(digest, config, today)
        if not slack_ok:
            if webhook_url:
                post_error(webhook_url, "news-digestのSlack配信 (再実行) に失敗しました")
            sys.exit(1)
        return

    markdown_text = render_newspaper(digest, config)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SUMMARY_MD_PATH.write_text(markdown_text, encoding="utf-8")  # 確認用の控え

    obsidian_ok = distribute_to_obsidian(markdown_text, config, today)
    slack_ok, webhook_url = distribute_to_slack(digest, config, today, obsidian_saved=obsidian_ok)

    if not slack_ok or not obsidian_ok:
        failed = []
        if not slack_ok:
            failed.append("Slack配信")
        if not obsidian_ok:
            failed.append("Obsidian保存")
        message = f"news-digestの配信に一部失敗しました: {', '.join(failed)}"
        if webhook_url:
            post_error(webhook_url, message)
        print(f"[ERROR] {message}", file=sys.stderr)
        sys.exit(1)

    print("[INFO] Obsidian保存・Slack全文配信の両方に成功しました。")


if __name__ == "__main__":
    main()
