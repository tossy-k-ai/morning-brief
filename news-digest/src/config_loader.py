"""config.yaml の読み込み共通処理。"""

import os
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config.yaml"
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"
PROMPTS_DIR = PROJECT_ROOT / "prompts"

ARTICLES_JSON_PATH = DATA_DIR / "articles.json"
SUMMARY_JSON_PATH = DATA_DIR / "summary.json"  # STEP2の出力 (1面・カテゴリ面の構造化データ)
SUMMARY_MD_PATH = DATA_DIR / "summary.md"      # STEP3が描画した新聞面 (確認用の控え)
ENV_PATH = PROJECT_ROOT / ".env"


def load_dotenv(path=ENV_PATH):
    """.env の KEY=VALUE を、未設定の環境変数にだけ読み込む (値は表示しない)。

    run_daily.bat は自前で .env を読むので、これは distribute.py を単体で再実行するときのため。
    """
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def load_config(path=None):
    path = Path(path) if path else CONFIG_PATH
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)
