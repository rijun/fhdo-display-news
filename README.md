# FH Dortmund Display News Bot
Forward FH Dortmund news via a Telegram bot

### Setup

##### MariaDB

Database setup script:

```mariadb
create table news
(
    hash char(32) not null,
    news_date date not null,
    title text not null,
    content text null,
    news_type text not null
);

create unique index news_hash_uindex
    on news (hash);

create table users
(
    id int not null,
    name text null,
    debug boolean default false not null
);

create unique index users_id_uindex
    on users (id);

alter table users
    add constraint users_pk
        primary key (id);
```