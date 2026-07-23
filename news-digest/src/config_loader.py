"""config.yaml の読み込み共通処理。"""

from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config.yaml"
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"
PROMPTS_DIR = PROJECT_ROOT / "prompts"

ARTICLES_JSON_PATH = DATA_DIR / "articles.json"
SUMMARY_MD_PATH = DATA_DIR / "summary.md"


def load_config(path=None):
    path = Path(path) if path else CONFIG_PATH
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)
