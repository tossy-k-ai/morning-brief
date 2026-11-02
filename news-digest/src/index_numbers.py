"""株価指数の数値 (水準・騰落幅・騰落率) の検出と伏せ字化。

STEP2 (generate_summary.py) の検査と STEP3 のSlack本文の両方で同じ規則を使う。
"""

import re

# 例: 「日経平均が3万9000円」「ダウ 500ドル」「ナスダックが2%」「TOPIX 2800ポイント」
INDEX_NUMBER_RE = re.compile(
    r"(日経平均|日経225|TOPIX|ダウ|NYダウ|S&P\s?500|ナスダック|Nasdaq|Dow)[^。、]{0,12}?[0-9０-９][0-9０-９,，.．]*\s*(円|ドル|ポイント|pt|%|％)"
)

MASK_TEXT = "（数値略）"


def mask_index_numbers(text):
    """株価指数の数値部分を伏せ、(伏せた後の文字列, 伏せたか) を返す。指数名は残す。"""
    if not text:
        return text, False
    masked, count = INDEX_NUMBER_RE.subn(lambda m: m.group(1) + MASK_TEXT, text)
    return masked, count > 0
