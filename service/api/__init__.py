from .interfaces import api as interfaces_api
from flask import Blueprint
from flask_restplus import Api

api_blueprint = Blueprint('interfaces service', __name__)

api = Api(
    api_blueprint,
    title=f'Dependencies Service Public API',
    version='1.0',
    description='Service for managing interface dependencies between services',
)

api.add_namespace(interfaces_api, path='/v1')
