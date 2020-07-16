import configparser


class Config:
    def __init__(self):
        c = configparser.ConfigParser()
        c.read("config.ini")
        self.sql_user = c['sql']['user']
        self.sql_pass = c['sql']['passwd']
        self.sql_db = c['sql']['db']
        self.bot_token = c['bot']['token']
        self.debug = False
