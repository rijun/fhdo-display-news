import sys
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, MetaData, Table, Column, String, Boolean, and_
from sqlalchemy.engine.base import Connection, Engine
from sqlalchemy.sql import select, insert, delete

from display_news import config
from display_news.parsers import current_news, display_news


# conf = config.Config()

meta = MetaData()
engine: Engine
news: Table
users: Table


def main(use_sqlite=False, bot_token=None):
    global engine
    global news
    global users

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
        engine = create_engine()
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
        message = f"--- {header} ---\n" \
                  f"Datum: {n['date']}\n\n" \
                  f"{n['title']}\n" \
                  f"{n['content']}"

        for r in receiver_list:
            requests.get(url, params={'text': message, 'chat_id': r})


if __name__ == '__main__':
    sqlite = True if '--sqlite' in sys.argv else False
    if '--token' in sys.argv:
        token = sys.argv[sys.argv.index('--token') + 1]
    else:
        token = "DEBUG"
    main(use_sqlite=sqlite, bot_token=token)
