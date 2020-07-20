import hashlib
import sys
from datetime import datetime

import requests
from bs4 import BeautifulSoup

import database
import config

conf = config.Config()
conf.debug = True if '-d' in sys.argv else False

db = database.DatabaseHandler(conf.sql_user, conf.sql_pass, conf.sql_db)


def main():
    if not conf.debug:
        clean_db()
        check_new_receiver()
    get_news()


def clean_db():
    entries = db.run_select_query("SELECT checksum, date FROM news")
    # Delete any entry older than 2 weeks
    for i in entries:
        delta = i[1] - datetime.today().date()
        if delta.days <= -14:
            db.run_query("DELETE FROM news WHERE checksum = %s", i[0])


def check_new_receiver():
    url = "https://api.telegram.org/bot{}/getUpdates".format(conf.bot_token)
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
                requests.get("https://api.telegram.org/bot{}/sendMessage".format(conf.bot_token), params=payload)


def get_news():
    process_display_news()
    process_current_et_news()


def get_page_contents(url):
    r = None
    try:
        r = requests.get(url)
    except TimeoutError:
        return None
    except requests.exceptions.ConnectionError:
        return None
    if r is None:
        return None
    page = BeautifulSoup(r.text, "html.parser")  # Parse html response and store it in the beautifulsoup format
    return page


def process_display_news():
    soup = get_page_contents("https://www.fh-dortmund.de/display")

    if soup is None:
        return

    checksum_list = [i[0] for i in db.run_select_query("SELECT checksum, date FROM news "
                                                       "WHERE type = 'DISPLAYNACHRICHT'")]

    news_title = soup.find(class_="newsHeadline")  # Find first news headline

    while news_title is not None:  # Search for content until every headline is processed
        if "FB 3" in news_title.string or "Studienbüro" in news_title.string:  # Sort out every non-relevent headline
            title = news_title.string
            data = news_title.find_next(class_="indent").string  # Next sibling after headline stores the news content
            checksum = hashlib.md5((title + data).encode('utf-8')).hexdigest()

            # Forward and store news only if there are no duplicates
            if checksum not in checksum_list:
                db.run_query("INSERT INTO news (checksum, title, content, date, type) VALUES (%s, %s, %s, %s, %s)",
                             checksum, str(title), str(data), datetime.today().date(), "DISPLAYNACHRICHT")
                send_telegram_message("**** DISPLAYNACHRICHT ****\n", title, data)

        news_title = news_title.find_next(class_="newsHeadline")  # Find next headline


def process_current_et_news():
    soup = get_page_contents("https://www.fh-dortmund.de/de/fb/3/studiengaenge/et/aktuelles/index.php")

    if soup is None:
        return

    checksum_list = [i[0] for i in db.run_select_query("SELECT checksum, date FROM news "
                                                       "WHERE type = 'AKTUELLES ET'")]

    news_title = soup.find('h2')  # Find first news headline

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

        # Forward and store news only if there are no duplicates
        if checksum not in checksum_list:
            db.run_query("INSERT INTO news (checksum, title, content, date, type) VALUES (%s, %s, %s, %s, %s)",
                         checksum, str(title), "", datetime.today().date(), "AKTUELLES ET")
            send_telegram_message("**** AKTUELLES ET ****\n", title)

        news_title = news_title.find_next('h2')  # Find next headline


def send_telegram_message(source, header, content=""):
    if conf.debug:
        query = "SELECT id FROM users WHERE debug = 1;"
    else:
        query = "SELECT id FROM users;"
    receiver_list = db.run_select_query(query)

    for receiver in receiver_list:
        message = source + '\n' + header + '\n' + content
        url = "https://api.telegram.org/bot{}/sendMessage".format(conf.bot_token)
        payload = {'text': message, 'chat_id': receiver}
        requests.get(url, params=payload)


if __name__ == '__main__':
    main()
