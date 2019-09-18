import configparser
import hashlib
from datetime import datetime
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup

import database


def get_news():
    clean_db()
    check_new_receiver()
    url = "https://www.fh-dortmund.de/display"
    r = requests.get(url)
    page = BeautifulSoup(r.text, "html.parser")  # Parse html response and store it in the beautifulsoup format
    process_page(page)


def clean_db():
    entries = db.run_select_query("SELECT checksum, date FROM news")
    # Delete any entry older than 2 weeks
    for i in entries:
        delta = i[1] - datetime.today().date()
        if delta.days <= -14:
            db.run_query("DELETE FROM news WHERE checksum = %s", i[0])


def check_new_receiver():
    url = "https://api.telegram.org/bot{}/getUpdates".format(config['bot'])
    r = requests.get(url)
    res = r.json()

    if not res:
        return

    receiver_list = db.run_select_query("SELECT id FROM users;")
    for item in res['result']:
        text = item['message']['text']
        if text == "/abonnieren":
            sender_id = item['message']['from']['id']
            if sender_id not in receiver_list:
                sender = item['message']['from']['first_name']
                db.run_query("INSERT INTO users (id, name) VALUES (%s, %s)", sender_id, sender)
                payload = {'text': "Erfolgreich abonniert!", 'chat_id': sender_id}
                requests.get("https://api.telegram.org/bot{}/sendMessage".format(config['bot']), params=payload)


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
                db.run_query("INSERT INTO news (checksum, title, content, date) VALUES (%s, %s, %s, %s)",
                             checksum, title, data, datetime.today().date())
                send_telegram_message(title, data)

        news_title = news_title.find_next(class_="newsHeadline")  # Find next headline


def send_telegram_message(header, content):
    receiver_list = db.run_select_query("SELECT id FROM users;")

    for receiver in receiver_list:
        message = quote_plus(header + '\n' + content)  # Encode message
        url = "https://api.telegram.org/bot{}/sendMessage".format(config['bot'])
        payload = {'text': message, 'chat_id': receiver}
        requests.get(url, params=payload)


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
