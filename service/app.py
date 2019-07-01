from flask import Flask
from service.api import api_blueprint
from service.config import get_config
from service.database import teardown_db_connection


def teardown_appcontext(exception=None):
    teardown_db_connection(exception)


def create_app():
    app = Flask(import_name='dependencies server')
    app.config.from_object(get_config())
    app.register_blueprint(api_blueprint, url_prefix='/api')
    app.teardown_appcontext(teardown_appcontext)
    return app


app = create_app()


if __name__ == '__main__':
    app.run(debug=True, use_debugger=False)
