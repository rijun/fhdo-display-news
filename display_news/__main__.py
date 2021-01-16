import logging
import sys
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, MetaData, Table, Column, String, Boolean, and_
from sqlalchemy.engine.base import Connection, Engine
from sqlalchemy.sql import select, insert, delete

from display_news import configuration
from display_news.parsers import current_news, display_news


meta = MetaData()
engine: Engine
news: Table
users: Table


def main(use_sqlite=False):
    global engine
    global news
    global users

    bot_token = configuration.bot_settings['token']
    if bot_token is None:
        logging.error("Bot token not supplied. Use --token option if debugging.")
        exit(-1)

    if use_sqlite:
        engine = create_engine('sqlite:///database.db', echo=True)
        news = Table('news', meta,
                     Column('hash', String),
                     Column('news_date', String),
                     Column('title', String),
                     Column('content', String),
                     Column('news_type', String)
                     )
        users = Table('users', meta,
                      Column('id', String),
                      Column('name', String),
                      Column('debug', Boolean)
                      )
        meta.create_all(engine)
    else:
        engine = create_engine(
            f"mysql+pymsql://"
            f"{configuration.sql_settings['user']}:"
            f"{configuration.sql_settings['passwd']}@"
            f"{configuration.sql_settings['host']}/"
            f"{configuration.sql_settings['dbname']}?"
            f"charset=utf8mb4"
        )
        news = Table('news', meta, autoload=True, autoload_with=engine)
        users = Table('users', meta, autoload=True, autoload_with=engine)

    conn = engine.connect()

    check_new_receiver(conn, bot_token)

    dn_url = "https://www.fh-dortmund.de/display"
    cn_url = "https://www.fh-dortmund.de/de/fb/3/studiengaenge/et/aktuelles/index.php"

    dn = display_news.parse(get_page_contents(dn_url))
    cn = current_news.parse(get_page_contents(cn_url))

    dn_filtered = filter_news(conn, dn, 'display')
    cn_filtered = filter_news(conn, cn, 'current')

    store_news(conn, dn_filtered, 'display')
    store_news(conn, cn_filtered, 'current')

    forward_message(conn, bot_token, dn_filtered, 'display')
    forward_message(conn, bot_token, cn_filtered, 'current')

    clean_db(conn, dn, 'display')
    clean_db(conn, cn, 'current')


def check_new_receiver(connection: Connection, bot_token: str):
    if bot_token == "DEBUG":
        return

    r = requests.get(f"https://api.telegram.org/bot{bot_token}/getUpdates")
    res = r.json()

    if not res:
        return

    q = select([users.c.id])
    receiver_list = [int(x[0]) for x in connection.execute(q).fetchall()]

    for item in res['result']:
        text = item['message']['text']
        if text == "/abonnieren":
            sender_id = item['message']['from']['id']
            if sender_id not in receiver_list:
                sender = item['message']['from']['first_name']
                ins = users.insert().values(
                    id=sender_id,
                    name=sender,
                    debug=False
                )
                connection.execute(ins)
                payload = {'text': "Erfolgreich abonniert!", 'chat_id': sender_id}
                requests.get("https://api.telegram.org/bot{}/sendMessage".format(bot_token), params=payload)


def get_page_contents(url):
    r = None
    try:
        r = requests.get(url)
    except TimeoutError:
        return
    except requests.exceptions.ConnectionError:
        return
    except Exception as e:
        print(e)
    if r is None:
        return
    page = BeautifulSoup(r.text, "html.parser")
    return page


def filter_news(connection: Connection, news_list: list, news_type: str) -> list:
    s = select([news.c.hash]).where(news.c.news_type == news_type)
    news_in_db = [i[0] for i in connection.execute(s)]
    filtered_news = [i for i in news_list if i['hash'] not in news_in_db]
    return filtered_news


def store_news(connection: Connection, news_list: list, news_type: str):
    for n in news_list:
        ins = news.insert().values(
            hash=n['hash'],
            news_date=n['date'],
            title=n['title'],
            content=n['content'],
            news_type=news_type
        )
        connection.execute(ins)


def forward_message(connection: Connection, bot_token: str, news_list: list, news_type: str, debug=False):
    if debug:
        q = select([users.c.id]).where(users.c.debug == 1)
    else:
        q = select([users.c.id])

    receivers = [int(x[0]) for x in connection.execute(q).fetchall()]
    send_telegram_message(bot_token, receivers, news_list, news_type)


def clean_db(connection: Connection, news_list: list, news_type: str):
    hash_list = [x['hash'] for x in news_list]
    s = select([news.c.hash]).where(and_(news.c.news_type == news_type, ~news.c.hash.in_(hash_list)))
    for i in connection.execute(s):
        d = news.delete().where(news.c.hash == i[0])
        connection.execute(d)


def send_telegram_message(bot_token: str, receiver_list: list, news_list: list, news_type: str):
    url = "https://api.telegram.org/bot{}/sendMessage".format(bot_token)

    if news_type == 'display':
        header = "Displaynachricht"
    elif news_type == 'current':
        header = "Aktuelles ET"
    else:
        return

    for n in news_list:
        message = f"---- {header} ----\n" \
                  f"<i>Datum: {n['date'].strftime('%d.%m.%Y')}</i>\n\n" \
                  f"<b>{n['title']}</b>\n\n" \
                  f"{n['content']}"

        for recv in receiver_list:
            r = requests.get(url, params={'text': message, 'chat_id': recv, 'parse_mode': 'HTML'})
            if r.status_code != 200:
                logging.warning("Status code: %s", r.status_code)
                logging.warning("Description: %s\n", r.content)


if __name__ == '__main__':
    sqlite = True if '--sqlite' in sys.argv else False
    if '--token' in sys.argv:
        configuration.bot_settings['token'] = "DEBUG"
    main(use_sqlite=sqlite)
