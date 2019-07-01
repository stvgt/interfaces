from flask import current_app, g
from psycopg2 import connect
from werkzeug.local import LocalProxy


def get_db_connection():
    connection = getattr(g, 'connection', None)
    if connection is None:
        config = current_app.config
        connection = g.connection = connect(
            host=config['POSTGRES_DB_HOST'],
            port=config['POSTGRES_DB_PORT'],
            dbname=config['POSTGRES_DB_NAME'],
            user=config['POSTGRES_DB_USER'],
            password=config['POSTGRES_DB_PASS'],
        )
    return connection


def teardown_db_connection(exception):
    connection = g.get('connection')
    if connection is not None:
        connection.close()

db_connection = LocalProxy(get_db_connection)
