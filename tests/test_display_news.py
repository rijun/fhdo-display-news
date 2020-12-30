from unittest import TestCase

from bs4 import BeautifulSoup

from display_news import __main__


class TestDisplayNews(TestCase):
    def test_parse_display_news(self):
        with open("display_news.html", 'r') as f:
            data = BeautifulSoup(f.readlines(), "html.parser")
        print(__main__.parse_display_news(data))
        self.fail()
