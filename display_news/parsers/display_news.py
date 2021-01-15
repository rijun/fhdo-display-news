import datetime
import hashlib

from bs4 import BeautifulSoup


def parse(data: BeautifulSoup) -> list:
    if data is None:
        return []

    news = []
    news_title = data.find(class_='newsHeadline')  # Find first news headline
    while news_title is not None:  # Search for content until every headline is processed
        title = news_title.string
        title = ' '.join(title.split())
        # Next sibling after headline stores the news content
        content = news_title.find_next(class_='indent').string
        content = ' '.join(content.split())
        news.append({
            'hash': hashlib.md5((title + content).encode('utf-8')).hexdigest(),
            'date': datetime.date.today(),
            'title': title,
            'content': content
        })
        news_title = news_title.find_next(class_="newsHeadline")  # Find next headline

    return news
