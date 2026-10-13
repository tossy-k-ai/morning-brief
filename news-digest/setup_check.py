"""セットアップ自己診断スクリプト。

Windows側で `python setup_check.py` を実行すると、news-digest を動かすのに
必要な前提が揃っているかを1つずつ確認し、足りないものを指摘する。

モデルの呼び出しもSlackへの投稿も行わないので、何度実行してもコストはかからない。
実際の配信テストは `run_daily.bat`（または `python src/distribute.py`）で行うこと。
"""

import importlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

results = []


def record(ok, label, detail="", warn=False):
    results.append((ok, label, detail, warn))
    mark = "WARN" if warn else ("PASS" if ok else "FAIL")
    line = f"[{mark}] {label}"
    if detail:
        line += f"\n       {detail}"
    print(line)


def check_python_version():
    v = sys.version_info
    ok = (v.major, v.minor) >= (3, 10)
    record(ok, f"Python {v.major}.{v.minor}.{v.micro}",
           "" if ok else "Python 3.10以降が必要です。")


def check_packages():
    for module, pip_name in [("requests", "requests"), ("feedparser", "feedparser"), ("yaml", "PyYAML")]:
        try:
            importlib.import_module(module)
            record(True, f"パッケージ {pip_name}")
        except ImportError:
            record(False, f"パッケージ {pip_name}", "pip install -r requirements.txt を実行してください。")


def check_timezone():
    """Windowsでは tzdata パッケージが無いと zoneinfo が動かない。"""
    try:
        from zoneinfo import ZoneInfo
        ZoneInfo("Asia/Tokyo")
        record(True, "タイムゾーン Asia/Tokyo")
    except Exception as exc:
        record(False, "タイムゾーン Asia/Tokyo",
               f"{exc} / Windowsでは `pip install tzdata` が必要です。")


def load_config():
    try:
        import yaml
        with open(PROJECT_ROOT / "config.yaml", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        record(True, "config.yaml の読み込み")
        return config
    except Exception as exc:
        record(False, "config.yaml の読み込み", str(exc))
        return None


def check_claude_cli(config):
    cli_path = (config or {}).get("claude", {}).get("cli_path", "claude")
    resolved = shutil.which(cli_path)
    if resolved is None and not Path(cli_path).exists():
        record(False, f"claude CLI ({cli_path})",
               "PATHに見つかりません。config.yaml の claude.cli_path にフルパスを設定してください。")
        return
    try:
        proc = subprocess.run(
            [cli_path, "--version"], capture_output=True, text=True,
            encoding="utf-8", timeout=60,
        )
        if proc.returncode == 0:
            record(True, "claude CLI", proc.stdout.strip())
        else:
            record(False, "claude CLI", f"--version が終了コード {proc.returncode}: {proc.stderr.strip()[:200]}")
    except Exception as exc:
        record(False, "claude CLI", str(exc))


def check_no_api_key():
    """ANTHROPIC_API_KEY が設定されていると、Proサブスクではなく従量課金APIが使われる恐れがある。"""
    if os.environ.get("ANTHROPIC_API_KEY"):
        record(False, "ANTHROPIC_API_KEY が未設定であること",
               "設定されています。このプロジェクトはProサブスク認証で動かす前提なので、"
               "従量課金が発生しないよう解除を検討してください。", warn=True)
    else:
        record(True, "ANTHROPIC_API_KEY が未設定であること")


def load_dotenv_if_present():
    """run_daily.bat と同じく .env を読み込む（このスクリプト単体実行時のため）。"""
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


def check_slack_webhook(config):
    var_name = (config or {}).get("slack", {}).get("webhook_env_var", "SLACK_WEBHOOK_URL")
    value = os.environ.get(var_name, "")
    if not value:
        record(False, f"{var_name}", ".env に設定してください（.env.example を参照）。")
    elif not value.startswith("https://hooks.slack.com/"):
        record(False, f"{var_name}", "値がSlack Webhookの形式ではないようです。", warn=True)
    else:
        record(True, f"{var_name}", "設定済み（値は表示しません）")


def check_obsidian_path(config):
    vault_path = (config or {}).get("obsidian", {}).get("vault_path")
    if not vault_path:
        record(False, "Obsidian vault_path", "config.yaml に obsidian.vault_path がありません。")
        return

    path = Path(vault_path)
    if not path.parent.exists():
        record(False, f"Obsidian vault_path ({vault_path})",
               f"親フォルダが存在しません: {path.parent} / 実際のVaultパスに書き換えてください。")
        return

    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".news_digest_write_test"
        probe.write_text("test", encoding="utf-8")
        probe.unlink()
        record(True, f"Obsidian vault_path ({vault_path})", "書き込み可能")
    except Exception as exc:
        record(False, f"Obsidian vault_path ({vault_path})", f"書き込めません: {exc}")


def check_work_dirs():
    for name in ["data", "logs"]:
        path = PROJECT_ROOT / name
        try:
            path.mkdir(parents=True, exist_ok=True)
            probe = path / ".write_test"
            probe.write_text("test", encoding="utf-8")
            probe.unlink()
            record(True, f"{name}/ フォルダ", "書き込み可能")
        except Exception as exc:
            record(False, f"{name}/ フォルダ", f"書き込めません: {exc}")


def main():
    print("=== news-digest セットアップ自己診断 ===\n")
    load_dotenv_if_present()

    check_python_version()
    check_packages()
    check_timezone()
    config = load_config()
    check_claude_cli(config)
    check_no_api_key()
    check_slack_webhook(config)
    check_obsidian_path(config)
    check_work_dirs()

    failures = [r for r in results if not r[0] and not r[3]]
    warnings = [r for r in results if r[3]]

    print("\n=== 結果 ===")
    print(f"PASS: {len([r for r in results if r[0]])} / FAIL: {len(failures)} / WARN: {len(warnings)}")

    if failures:
        print("\n未解決の項目:")
        for _, label, detail, _ in failures:
            print(f"  - {label}: {detail}")
        print("\n上記を解消してから run_daily.bat を実行してください。")
        sys.exit(1)

    print("\n前提条件はすべて満たしています。次は run_daily.bat を実行して、")
    print("Slackへの配信とObsidianへの保存を実際に確認してください。")
    sys.exit(0)


if __name__ == "__main__":
    main()
