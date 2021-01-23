import logging
import sys

import requests
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, sql

from display_news import configuration
from display_news.parsers import current_news, display_news


def main():
    bot_token = configuration.bot_settings['token']
    if bot_token is None:
        logging.error("Bot token not supplied. Use --token option if debugging.")
        return -1

    database = create_engine(
        f"mysql+pymysql://"
        f"{configuration.sql_settings['user']}:"
        f"{configuration.sql_settings['passwd']}@"
        f"{configuration.sql_settings['host']}/"
        f"{configuration.sql_settings['dbname']}"
        f"?charset=utf8mb4"
    )

    check_receiver_change(database, bot_token)

    dn_url = "https://www.fh-dortmund.de/display"
    cn_url = "https://www.fh-dortmund.de/de/fb/3/studiengaenge/et/aktuelles/index.php"

    dn = display_news.parse(get_page_contents(dn_url))
    cn = current_news.parse(get_page_contents(cn_url))

    dn_filtered = filter_news(database, dn, 'display')
    cn_filtered = filter_news(database, cn, 'current')

    store_news(database, dn_filtered, 'display')
    store_news(database, cn_filtered, 'current')

    forward_message(database, bot_token, dn_filtered, 'display')
    forward_message(database, bot_token, cn_filtered, 'current')

    clean_db(database, dn, 'display')
    clean_db(database, cn, 'current')


def check_receiver_change(engine, bot_token):
    """Check if a new receiver has subscribed or if a existing receiver has unsubscribed, and then add or remove them
    from the database."""
    if bot_token == "DEBUG":
        return

    receiver_list = [int(x[0]) for x in engine.execute(sql.text("SELECT id FROM users"))]

    r = requests.get(f"https://api.telegram.org/bot{bot_token}/getUpdates")
    res = r.json()

    if not res:
        return

    for item in res['result']:
        text = item['message']['text']
        sender_id = item['message']['from']['id']
        if text == "/start":
            if sender_id not in receiver_list:
                sender = item['message']['from']['first_name']
                query = sql.text("INSERT INTO users VALUES (:sender_id, :sender_name, :debug)")
                engine.execute(query, sender_id, sender, False)
                receiver_list.append(sender_id)
                payload = {'text': "Erfolgreich abonniert!", 'chat_id': sender_id}
                requests.get("https://api.telegram.org/bot{}/sendMessage".format(bot_token), params=payload)
        elif text == "/stop":
            if sender_id not in receiver_list:
                sender = item['message']['from']['first_name']
                query = sql.text("DELETE FROM users VALUES WHERE id = :sender_id")
                engine.execute(query, sender_id, sender, False)
                receiver_list.remove(sender_id)
                payload = {'text': "Erfolgreich entabonniert!", 'chat_id': sender_id}
                requests.get("https://api.telegram.org/bot{}/sendMessage".format(bot_token), params=payload)


def get_page_contents(url):
    """Get the HTML text from the web page passed via the URL parameter and return a BeautifulSoup object."""
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


def filter_news(engine, news_list, news_type):
    """Filter out news which is already present in the database."""
    query = sql.text("SELECT hash FROM news WHERE news_type = :news_type")
    data = {
        'news_type': news_type
    }
    news_in_db = [i[0] for i in engine.execute(query, data)]
    filtered_news = [i for i in news_list if i['hash'] not in news_in_db]
    return filtered_news


def store_news(engine, news_list, news_type):
    """Store news in the database."""
    for n in news_list:
        query = sql.text("INSERT INTO news VALUES (:hash, :news_date, :title, :content, :news_type)")
        data = {
            'hash': n['hash'],
            'news_date': n['date'],
            'title': n['title'],
            'content': n['content'],
            'news_type': news_type
        }
        engine.execute(query, data)


def forward_message(engine, bot_token, news_list, news_type, debug=False):
    """Forward news to each receiver."""
    if debug:
        query = sql.text("SELECT id FROM users WHERE debug is TRUE")
    else:
        query = sql.text("SELECT id FROM users")

    receivers = [int(x[0]) for x in engine.execute(query)]
    send_telegram_message(bot_token, receivers, news_list, news_type)


def clean_db(engine, news_list, news_type):
    """Remove news which is not available anymore on the website."""
    hash_list = [x['hash'] for x in news_list]
    data = {
        'hash_list': hash_list,
        'news_type': news_type
    }
    query = sql.text("SELECT hash FROM news WHERE hash NOT IN :hash_list AND news_type = :news_type")
    for i in engine.execute(query, data):
        engine.execute(sql.text("DELETE FROM news WHERE hash = :hash"), {'hash': i[0]})


def send_telegram_message(bot_token, receiver_list, news_list, news_type):
    """Format news and send it via a telegram bot."""
    url = "https://api.telegram.org/bot{}/sendMessage".format(bot_token)

    if news_type == 'display':
        header = "Displaynachricht"
    elif news_type == 'current':
        header = "Aktuelles ET"
    else:
        return

    for n in news_list:
        message = f"++++ {header} ++++\n" \
                  f"<i>Datum: {n['date'].strftime('%d.%m.%Y')}</i>\n\n" \
                  f"<b>{n['title']}</b>\n\n" \
                  f"{n['content']}"

        for recv in receiver_list:
            r = requests.get(url, params={'text': message, 'chat_id': recv, 'parse_mode': 'HTML'})
            if r.status_code != 200:
                logging.warning("Status code: %s", r.status_code)
                logging.warning("Description: %s\n", r.content)


if __name__ == '__main__':
    if '--token' in sys.argv:
        configuration.bot_settings['token'] = "DEBUG"
    exit(main())
