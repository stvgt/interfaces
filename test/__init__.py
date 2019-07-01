import os
from werkzeug.utils import import_string
from service.config import set_config

set_config(import_string(os.environ.get('APP_CONFIG', 'service.config.TestConfig')))
