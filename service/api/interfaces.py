import json
from dataclasses import asdict

import yaml
from flask import request
from flask_restplus import Namespace, Resource, abort
from jsonschema import ValidationError
from werkzeug.datastructures import FileStorage

from service.database import db_connection
from service.database.queries import (
    get_components,
    set_interface,
    InterfaceEntryDuplication,
    InterfaceEntryConflict,
)
from service.util.parse_interfaces_yaml import YamlParser

ARGUMENT_YAML_FILE = 'yaml_file'

api = Namespace(
    name='interfaces',
    description='Service for managing interfaces',
    path='/',
)

interfaces_yaml_put_parser = api.parser()
interfaces_yaml_put_parser.add_argument(
    ARGUMENT_YAML_FILE,
    type=FileStorage,
    location='files',
    required=True,
    help='A yaml file with the interface declaration for the given component',
)


@api.route('/components/<string:component_identifier>/interfaces/yaml')
@api.doc(params={
    'component_identifier': 'The component identifier, e.g. a name.',
    'yaml_file': 'A yaml file with the interface declaration for the given component.'
})
class InterfacesYamlApi(Resource):
    @api.expect(interfaces_yaml_put_parser)
    def put(self, component_identifier: str):
        num_files = len(request.files.getlist(ARGUMENT_YAML_FILE))
        if num_files != 1:
            abort(400, f'Num files = {num_files}, expected 1.')
        file = request.files[ARGUMENT_YAML_FILE]

        try:
            consumers, producers = YamlParser().parse(file.stream)
            set_interface(db_connection, component_identifier, consumers, producers)

        except (yaml.YAMLError) as e:
            abort(400, f'The file is no valid YAMl: {e}')
        except (ValidationError, InterfaceEntryDuplication) as e:
            abort(400, f'The file is not valid: {e}')
        except (InterfaceEntryConflict) as e:
            abort(
                409,
                f'Changing the interface of "{component_identifier}" not possible due to conflicting requirements: {e}')

        return {}, 200


components_get_parser = api.parser()


@api.route('/components')
class InterfacesYamlApi(Resource):
    @api.expect(components_get_parser)
    def get(self):
        components = get_components(db_connection)
        response = [asdict(component) for component in components]

        return response, 200
