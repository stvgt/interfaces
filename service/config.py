import os
from werkzeug.utils import import_string


class DefaultConfig:
    POSTGRES_DB_HOST = os.environ.get('POSTGRES_DB_HOST', 'localhost')
    POSTGRES_DB_PORT = os.environ.get('POSTGRES_DB_PORT', '5432')
    POSTGRES_DB_NAME = os.environ.get('POSTGRES_DB_NAME', 'interfaces')
    POSTGRES_DB_USER = os.environ.get('POSTGRES_DB_USER', 'postgres')
    POSTGRES_DB_PASS = os.environ.get('POSTGRES_DB_PASS', 'postgres')


class ProductionConfig(DefaultConfig):
    USE_DEBUGGER = False


class TestConfig(DefaultConfig):
    POSTGRES_DB_NAME = os.environ.get('POSTGRES_DB_NAME', 'interfaces_test')
    TESTING = True


_CONFIG = None


def set_config(config):
    """
    Sets the config. CAUTION: Must NOT be called after config is already used (get_config) or set (set_config).
    """
    global _CONFIG
    if _CONFIG is not None:
        raise Exception('It is not safe to change the app config after get_config was already called.')
    _CONFIG = config


def get_config():
    global _CONFIG
    if _CONFIG is None:
        _CONFIG = import_string(os.environ.get('APP_CONFIG', 'service.config.ProductionConfig'))
    return _CONFIG
