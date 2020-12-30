import hashlib

from bs4 import BeautifulSoup


def parse(data: BeautifulSoup) -> list:
    if data is None:
        return []

    news = []
    news_title = data.find(class_="article float-break")    # Find first news headline

    while news_title is not None:  # Search for content until every headline is processed
        for p in news_title.parents:
            if p.has_attr('id') and p['id'] == 'footer':
                return

        title = news_title.string.strip()
        # data = ""  # Next sibling after headline stores the news content
        # for c in news_title.find_next('td').children:
        #     if c.name == 'p':
        #         data += c.text
        # print(data)
        checksum = hashlib.md5(title.encode('utf-8')).hexdigest()

        news_title = news_title.find_next('h2')  # Find next headline

    return news
