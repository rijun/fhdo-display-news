import configparser
import os


class Config:
    def __init__(self):
        c = configparser.ConfigParser()
        config_file = os.path.join(os.path.dirname(__file__), "config.ini")
        c.read(config_file)
        self.sql_user = c['sql']['user']
        self.sql_pass = c['sql']['passwd']
        self.sql_db = c['sql']['db']
        self.bot_token = c['bot']['token']
        self.debug = False
