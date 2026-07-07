"""Web crawler — delegates to shared/web_search for content extraction."""

from shared.web_search import extract_content


def crawl(url: str):
    return extract_content(url)
