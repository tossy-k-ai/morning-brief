"""重複除去: URL完全一致 + タイトルの高類似度判定。"""

from difflib import SequenceMatcher


def dedupe_by_url(articles):
    """url完全一致の重複を除去する（最初に出てきたものを残す）。"""
    seen = set()
    result = []
    for article in articles:
        url = article["url"]
        if url in seen:
            continue
        seen.add(url)
        result.append(article)
    return result


def title_similarity(title_a, title_b):
    return SequenceMatcher(None, title_a, title_b).ratio()


def dedupe_by_title_similarity(articles, threshold):
    """タイトルの類似度がthreshold以上のものを重複とみなし、最初に出てきたものを残す。"""
    result = []
    for article in articles:
        is_duplicate = any(
            title_similarity(article["title"], kept["title"]) >= threshold
            for kept in result
        )
        if not is_duplicate:
            result.append(article)
    return result


def dedupe_articles(articles, title_similarity_threshold=0.85):
    articles = dedupe_by_url(articles)
    articles = dedupe_by_title_similarity(articles, title_similarity_threshold)
    return articles
