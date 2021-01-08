import hashlib

from bs4 import BeautifulSoup

from . import format_text


def parse(data: BeautifulSoup) -> list:
    if data is None:
        return []

    news = []

    for article in data.find_all(class_="article float-break"):
        title = format_text(article.previous_sibling.previous_sibling.text)
        raw_text = article.find(class_="text")
        date = ""
        content_list = []
        for i, child in enumerate(raw_text.children):
            if child == '\n':
                continue
            if not date and child.name == 'p':
                date = format_text(child.get_text())
                continue
            elif child.name == 'p':
                content_list.append(format_text(child.get_text().strip()))
            elif child.name == 'ul':
                for list_item in child.children:
                    if list_item.name is not None:
                        content_list.append(f"- {format_text(list_item.get_text())}")
            elif child.name == 'table':
                for table_row in child.tbody.children:
                    if table_row.name != 'tr':
                        continue
                    for table_data in table_row.children:
                        if table_data.name != 'td':
                            continue
                        for paragraph in table_data.children:
                            if paragraph.name is not None:
                                content_list.append(format_text(paragraph.get_text()))
        content = '\n'.join(content_list).strip()
        news.append({
            'hash': hashlib.md5((title + content).encode('utf-8')).hexdigest(),
            'date': date,
            'title': title,
            'content': content
        })

    return news
