import configparser
import hashlib
from datetime import datetime
from urllib.parse import quote_plus
from urllib.request import urlopen

from bs4 import BeautifulSoup

import database


def get_news():
    clean_db()
    fhdo_url = "https://www.fh-dortmund.de/display"
    page = urlopen(fhdo_url)  # Query the website and return the html response
    parsed_page = BeautifulSoup(page, "html.parser")  # Parse html response and store it in the beautifulsoup format
    process_page(parsed_page)


def clean_db():
    entries = db.run_select_query("SELECT checksum, date FROM news")
    # Delete any entry older than 2 weeks
    for i in entries:
        delta = i[1] - datetime.today().date()
        if delta.days <= -14:
            db.run_query("DELETE FROM news WHERE checksum = '{}'".format(i[0]))


def process_page(soup):
    checksum_list = [i[0] for i in db.run_select_query("SELECT checksum, date FROM news")]

    news_title = soup.find(class_="newsHeadline")  # Find first news headline

    while not (news_title is None):  # Search for content until every headline is processed
        if "FB 3" in news_title.string or "Studienbüro" in news_title.string:  # Sort out every non-relevent headline
            title = news_title.string
            data = news_title.find_next(class_="indent").string  # Next sibling after headline stores the news content
            checksum = hashlib.md5((title + data).encode('utf-8')).hexdigest()

            # Forward and store news only if there are no duplicates
            if checksum not in checksum_list:
                db.run_query("INSERT INTO news (checksum, title, content, date) "
                             "VALUES ('{0}', '{1}', '{2}', '{3}')"
                             .format(checksum, title, data, datetime.today().date()))
                send_telegram_message(title, data)

        news_title = news_title.find_next(class_="newsHeadline")  # Find next headline


def send_telegram_message(header, content):
    receiver_list = db.run_select_query("SELECT id FROM users;")

    for receiver in receiver_list:
        message = quote_plus(header + '\n' + content)  # Encode message
        url = "https://api.telegram.org/bot{}/sendMessage?text={}&chat_id={}".format(config['bot'], message, receiver)
        urlopen(url)


def read_configfile(filename):
    c = configparser.ConfigParser()
    c.read(filename)
    configuration = {
        "sql_user": c['sql']['user'],
        "sql_pass": c['sql']['passwd'],
        "sql_db": c['sql']['db'],
        "bot": c['bot']['token']
    }
    return configuration


if __name__ == '__main__':
    config = read_configfile("config.ini")
    db = database.DatabaseHandler(config['sql_user'], config['sql_pass'], config['sql_db'])
    get_news()
