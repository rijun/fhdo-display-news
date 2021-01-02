import json
from unittest import TestCase

from bs4 import BeautifulSoup

from display_news.parsers import display_news


class TestDisplayNews(TestCase):
    def setUp(self) -> None:
        with open("files/display_news.html", 'r') as f:
            self.file_data = BeautifulSoup(f, 'html.parser')

    def test_parser(self):
        data = display_news.parse(self.file_data)
        with open("files/display_news.json", 'r') as f:
            test_data = json.load(f)
        self.assertEqual(len(data), len(test_data))
        for i, d in enumerate(data):
            self.assertEqual(test_data[i]['title'], d['title'])
            self.assertEqual(test_data[i]['content'], d['content'])
