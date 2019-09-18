import mysql.connector as mariadb


class DatabaseHandler:
    def __init__(self, user, password, database):
        self.connection = mariadb.connect(user=user, password=password, database=database)
        self.cursor = self.connection.cursor()

    def run_select_query(self, query):
        """ Run a SQL SELECT query. """
        self.cursor.execute(query)

        # Clean SQL result because a single result tuple entry contains an extra space
        return_result = []
        for result in self.cursor.fetchall():
            if len(result) is 1:
                return_result.append(result[0])
            else:
                return_result.append(result)
        return return_result

    def run_query(self, query):
        """ Run a SQL query. """
        self.cursor.execute(query)
        self.connection.commit()
