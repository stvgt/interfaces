import os
import unittest

from service.util.parse_interfaces import ConsumerRecord, ProducerRecord
from service.util.parse_interfaces_yaml import YamlParser

TESTDATA_DIR = os.path.join(os.path.dirname(__file__), 'testdata')
CONSUMER1_YAML = 'consumer1.yaml'
PRODUCER1_YAML = 'producer1.yaml'
MIXED_YAML = 'mixed.yaml'

MY_SERVICE_RECORD = {
    'interface_host': 'my_service',
    'interface_type': 'rest',
    'primary': 'put',
    'secondary': '/api/v1/main_entity/<int:id>/sub_entity/<int:id>',
    'tertiary': '',
}

MAIN_DB_RECORD = {
    'interface_host': 'main_db_host',
    'interface_type': 'postgres_table',
    'primary': 'datasets_db',
    'secondary': 'shard_<id>',
    'tertiary': 'datasets',
}


class ParseInterfacesYamlTest(unittest.TestCase):
    def test_parse_producer(self):
        for filename, expected_consumer_records, expected_producer_records in (
            (
                os.path.join(TESTDATA_DIR, CONSUMER1_YAML),
                [
                    ConsumerRecord(sub_component='sub1', **MY_SERVICE_RECORD, optional=False),
                    ConsumerRecord(sub_component='sub1', ** MAIN_DB_RECORD, optional=True),
                ],
                [],
            ),
            (
                os.path.join(TESTDATA_DIR, PRODUCER1_YAML),
                [],
                [
                    ProducerRecord(sub_component='sub2', **MY_SERVICE_RECORD, deprecated=True),
                    ProducerRecord(sub_component='sub2', ** MAIN_DB_RECORD, deprecated=False),
                ],
            ),
            (
                os.path.join(TESTDATA_DIR, MIXED_YAML),
                [
                    ConsumerRecord(sub_component='sub1', **MY_SERVICE_RECORD, optional=False),
                    ConsumerRecord(sub_component='sub2', **MAIN_DB_RECORD, optional=True,
                    ),
                ],
                [
                    ProducerRecord(sub_component='sub2', **MY_SERVICE_RECORD, deprecated=True),
                    ProducerRecord(sub_component='sub3', **MAIN_DB_RECORD, deprecated=False),
                ],
            ),
        ):
            with self.subTest(filename):
                with open(filename, 'rb') as yaml_file:
                    consumer_records, producer_records = YamlParser().parse(yaml_file)
                    self.assertListEqual(consumer_records, expected_consumer_records)
                    self.assertListEqual(producer_records, expected_producer_records)
