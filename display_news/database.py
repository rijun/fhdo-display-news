import sys
import logging

import mariadb


class DatabaseHandler:
    def __init__(self, user, password, database):
        try:
            self.connection = mariadb.connect(user=user, password=password, database=database)
        except mariadb.Error as e:
            logging.error(f"Error connecting to MariaDB Platform: {e}")
            sys.exit(1)
        self.cursor = self.connection.cursor()

    def run_select_query(self, query):
        """ Run a SQL SELECT query. """
        self.cursor.execute(query)

        # Clean SQL result because a single result tuple entry contains an extra space
        return_result = []
        for result in self.cursor.fetchall():
            if len(result) == 1:
                return_result.append(result[0])
            else:
                return_result.append(result)
        return return_result

    def run_query(self, query, *args):
        """ Run a SQL query. """
        self.cursor.execute(query, args)
        self.connection.commit()
