import hashlib
import sys
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from display_news import config
from display_news.parsers import current_news, display_news

# conf = config.Config()

# db = database.DatabaseHandler(conf.sql_user, conf.sql_pass, conf.sql_db)


def main(dry_run=False):
    if not dry_run:
        from display_news import database
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
    # checksum_list = [i[0] for i in db.run_select_query("SELECT checksum, date FROM news "
    #                                                    "WHERE type = 'DISPLAYNACHRICHT'")]

    dn_data = display_news.parse(get_page_contents("https://www.fh-dortmund.de/display"))

    # Forward and store news only if there are no duplicates
    # if checksum not in checksum_list:
    #     db.run_query("INSERT INTO news (checksum, title, content, date, type) VALUES (%s, %s, %s, %s, %s)",
    #                  checksum, str(title), str(data), datetime.today().date(), "DISPLAYNACHRICHT")
    #     send_telegram_message("**** DISPLAYNACHRICHT ****\n", title, data)

    cn_data = current_news.parse(get_page_contents("https://www.fh-dortmund.de/de/fb/3/studiengaenge/et/aktuelles"
                                                   "/index.php"))

    for data in cn_data:
        send_telegram_message("---Aktuelles ET ---", data['title'], data['content'])

    # Forward and store news only if there are no duplicates
    # if checksum not in checksum_list:
    #     db.run_query("INSERT INTO news (checksum, title, content, date, type) VALUES (%s, %s, %s, %s, %s)",
    #                  checksum, str(title), "", datetime.today().date(), "AKTUELLES ET")
    #     send_telegram_message("**** AKTUELLES ET ****\n", title)


    # checksum_list = [i[0] for i in db.run_select_query("SELECT checksum, date FROM news WHERE type = 'AKTUELLES ET'")]


def get_page_contents(url):
    try:
        r = requests.get(url)
    except TimeoutError:
        return None
    except requests.exceptions.ConnectionError:
        return None
    except Exception as e:
        print(e)
    if r is None:
        return None
    page = BeautifulSoup(r.text, "html.parser")  # Parse html response and store it in the beautifulsoup format
    return page


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
    dr = True if '--dry_run' in sys.argv else False
    main(dry_run=dr)
