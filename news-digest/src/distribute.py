"""STEP3: summary.md を読み込み、Slack配信とObsidian保存の両方に届ける。

どちらかが失敗しても、もう片方は独立して試みる（ベストエフォート）。
"""

import os
import sys
from datetime import date

from config_loader import SUMMARY_MD_PATH, load_config
from obsidian_writer import write_daily_note
from slack_client import markdown_to_slack_blocks, post_error, post_message_in_chunks


def distribute_to_slack(markdown_text, config):
    webhook_env_var = config.get("slack", {}).get("webhook_env_var", "SLACK_WEBHOOK_URL")
    webhook_url = os.environ.get(webhook_env_var)
    if not webhook_url:
        print(f"[ERROR] 環境変数 {webhook_env_var} が設定されていません。Slack配信をスキップします。", file=sys.stderr)
        return False, None

    try:
        blocks = markdown_to_slack_blocks(markdown_text)
        post_message_in_chunks(webhook_url, blocks)
        print("[INFO] Slackへの配信に成功しました。")
        return True, webhook_url
    except Exception as exc:
        print(f"[ERROR] Slackへの配信に失敗しました: {exc}", file=sys.stderr)
        return False, webhook_url


def distribute_to_obsidian(markdown_text, config):
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
            today=date.today(),
        )
        print(f"[INFO] Obsidian Vaultへの保存に成功しました: {file_path}")
        return True
    except Exception as exc:
        print(f"[ERROR] Obsidian Vaultへの保存に失敗しました: {exc}", file=sys.stderr)
        return False


def main():
    config = load_config()

    if not SUMMARY_MD_PATH.exists():
        print(f"[ERROR] {SUMMARY_MD_PATH} が見つかりません。先に generate_summary.py を実行してください。", file=sys.stderr)
        sys.exit(1)

    with open(SUMMARY_MD_PATH, encoding="utf-8") as f:
        markdown_text = f.read()

    slack_ok, webhook_url = distribute_to_slack(markdown_text, config)
    obsidian_ok = distribute_to_obsidian(markdown_text, config)

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

    print("[INFO] Slack配信・Obsidian保存の両方に成功しました。")


if __name__ == "__main__":
    main()
