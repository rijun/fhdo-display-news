import configparser
import logging
import pathlib

CONFIG_PATH = "./config.ini"


class Configuration:
    def __init__(self):
        self.sql_settings = {}
        self.bot_settings = {}

    def read_configuration(self):
        """Stores the database and bot settings in the corresponding dictionaries."""
        config = configparser.ConfigParser()
        config.read(pathlib.Path(CONFIG_PATH))

        if not config.sections():   # Config file not found
            logging.error("config.ini not found")
            exit(-1)

        if 'sql' in config.sections():
            self.sql_settings = {
                'host': config['sql'].get('host', None),
                'user': config['sql'].get('user', None),
                'passwd': config['sql'].get('passwd', None),
                'dbname': config['sql'].get('dbname', None)
            }
        else:
            logging.error("SQL server settings not found")
            exit(-1)

        if 'bot' in config.sections():
            self.bot_settings = {
                'token': config['bot'].get('token', None)
            }
        else:
            logging.error("Bot settings not found")
            exit(-1)
