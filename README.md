# FH Dortmund Display News Bot
Forward FH Dortmund display news via a Telegram bot

### Setup
##### Required Python3 modules
    - Beautiful Soup
    - mysql-connector
##### Configuration file
Contents of ``config.ini``:
```
[sql]
user = <database_user>
passwd = <database_password>
db = <database_name>

[bot]
token = <your_bot_token>
```