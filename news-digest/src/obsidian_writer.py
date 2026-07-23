"""summary.md を Obsidian Vault の Daily Notes 形式で保存する。

Windowsのユーザー名に日本語が含まれる場合でも問題なく動くよう、
パス操作は pathlib、ファイルI/Oは明示的に UTF-8 で行う。
"""

from datetime import date
from pathlib import Path


def write_daily_note(summary_markdown, vault_path, filename_format="%Y-%m-%d.md", mode="append", today=None):
    today = today or date.today()
    vault_dir = Path(vault_path)
    vault_dir.mkdir(parents=True, exist_ok=True)

    filename = today.strftime(filename_format)
    file_path = vault_dir / filename

    if mode == "append" and file_path.exists():
        with open(file_path, "a", encoding="utf-8") as f:
            f.write("\n\n---\n\n")
            f.write(summary_markdown)
    else:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(summary_markdown)

    return file_path
