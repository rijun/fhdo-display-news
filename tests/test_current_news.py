from unittest import TestCase

from bs4 import BeautifulSoup

from display_news import __main__


class TestEtNews(TestCase):
    def test_parse_et_news(self):
        with open("current_news.html", 'r') as f:
            data = BeautifulSoup(f.read(), "html.parser")
        print(__main__.parse_et_news(data))
        self.fail()
