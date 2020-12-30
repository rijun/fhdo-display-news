import hashlib

from bs4 import BeautifulSoup


def parse(data: BeautifulSoup) -> list:
    if data is None:
        return []

    news = []
    news_title = data.find(class_="newsHeadline")  # Find first news headline
    while news_title is not None:  # Search for content until every headline is processed
        title = news_title.string
        data = news_title.find_next(class_="indent").string  # Next sibling after headline stores the news content
        news_hash = hashlib.md5((title + data).encode('utf-8')).hexdigest()
        news.append({
            'hash': news_hash,
            'title': title,
            'data': data
        })
        news_title = news_title.find_next(class_="newsHeadline")  # Find next headline

    return news
