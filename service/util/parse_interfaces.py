from itertools import chain
from typing import List, Iterator, Tuple

import jsonschema
from dataclasses import dataclass, asdict


@dataclass
class ConsumerValue:
    primary: str
    secondary: str
    tertiary: str
    optional: bool


@dataclass
class ConsumerRecord(ConsumerValue):
    sub_component: str
    interface_host: str
    interface_type: str


@dataclass
class ProducerValue:
    primary: str
    secondary: str
    tertiary: str
    deprecated: bool


@dataclass
class ProducerRecord(ProducerValue):
    sub_component: str
    interface_host: str
    interface_type: str


class Parser():
    API_VERSION = 'apiVersion'
    KIND = 'kind'
    SUB_COMPONENT = 'sub-component'
    PRODUCERS = 'producers'
    CONSUMERS = 'consumers'
    HOST = 'host'
    TYPE = 'type'
    VALUES = 'values'
    PRIMARY = 'primary'
    SECONDARY = 'secondary'
    TERTIARY = 'tertiary'
    OPTIONAL = 'optional'
    DEPRECATED = 'deprecated'

    SCHEMA = {
        'definitions': {
            'interface_declaration_v1': {
                'type': 'object',
                'properties': {
                    API_VERSION: {
                        'type': 'integer',
                        'minimum': 1,
                        'maximum': 1
                    },
                    KIND: {
                        'type': 'string',
                        'enum': ['InterfaceDeclaration']
                    },
                    SUB_COMPONENT: {
                        'type': 'string',
                    },
                    PRODUCERS: {
                        'type': 'array',
                        'items': {
                            '$ref': '#/definitions/producers_v1'
                        },
                    },
                    CONSUMERS: {
                        'type': 'array',
                        'items': {
                            '$ref': '#/definitions/consumers_v1'
                        },
                    }
                },
                'required': [API_VERSION, KIND]
            },
            'producers_v1': {
                'type': 'object',
                'properties': {
                    HOST: {
                        'type': 'string',
                    },
                    TYPE: {
                        'type': 'string',
                    },
                    VALUES: {
                        'type': 'array',
                        'items': {
                            '$ref': '#/definitions/producer_v1'
                        },
                    }
                },
                'required': [HOST, TYPE, VALUES]
            },
            'consumers_v1': {
                'type': 'object',
                'properties': {
                    HOST: {
                        'type': 'string',
                    },
                    TYPE: {
                        'type': 'string',
                    },
                    VALUES: {
                        'type': 'array',
                        'items': {
                            '$ref': '#/definitions/consumer_v1'
                        },
                    }
                },
                'required': [HOST, TYPE, VALUES]
            },
            'consumer_v1': {
                'type': 'object',
                'properties': {
                    PRIMARY: {
                        'type': 'string',
                    },
                    SECONDARY: {
                        'type': 'string',
                    },
                    TERTIARY: {
                        'type': 'string',
                    },
                    OPTIONAL: {
                        'type': 'boolean',
                    },
                },
            },
            'producer_v1': {
                'type': 'object',
                'properties': {
                    PRIMARY: {
                        'type': 'string',
                    },
                    SECONDARY: {
                        'type': 'string',
                    },
                    TERTIARY: {
                        'type': 'string',
                    },
                    DEPRECATED: {
                        'type': 'boolean',
                    },
                },
            },
        },
        'type': 'array',
        'items': {
            '$ref': '#/definitions/interface_declaration_v1'
        },
    }

    @classmethod
    def _validate_interfaces(cls, interfaces):
        jsonschema.validate(interfaces, cls.SCHEMA)

    def _parse_consumer_value(self, value: dict) -> ConsumerValue:
        return ConsumerValue(
            primary=value.get(self.PRIMARY, ''),
            secondary=value.get(self.SECONDARY, ''),
            tertiary=value.get(self.TERTIARY, ''),
            optional=value.get(self.OPTIONAL, False)
        )

    def _parse_producer_value(self, value: dict) -> ProducerValue:
        return ProducerValue(
            primary=value.get(self.PRIMARY, ''),
            secondary=value.get(self.SECONDARY, ''),
            tertiary=value.get(self.TERTIARY, ''),
            deprecated=value.get(self.DEPRECATED, False)
        )

    def _parse_consumer(self, sub_component: str, consumer: dict) -> Iterator[ConsumerRecord]:
        interface_host = consumer[self.HOST]
        interface_type = consumer[self.TYPE]
        for consumer_value in consumer[self.VALUES]:
            yield ConsumerRecord(
                sub_component=sub_component,
                interface_host=interface_host,
                interface_type=interface_type,
                **asdict(self._parse_consumer_value(consumer_value))
            )

    def _parse_producer(self, sub_component: str, producer: dict) -> Iterator[ProducerRecord]:
        interface_host: str = producer[self.HOST]
        interface_type: str = producer[self.TYPE]
        for producer_value in producer[self.VALUES]:
            yield ProducerRecord(
                sub_component=sub_component,
                interface_host=interface_host,
                interface_type=interface_type,
                **asdict(self._parse_producer_value(producer_value))
            )

    def _parse_interface(self, interface: dict) -> Tuple[Iterator[ConsumerRecord], Iterator[ProducerRecord]]:
        sub_component: str = interface.get(self.SUB_COMPONENT, '')
        consumers: list = interface.get(self.CONSUMERS, [])
        producers: list = interface.get(self.PRODUCERS, [])
        consumer_records_iter: Iterator[ConsumerRecord] = chain.from_iterable(
            self._parse_consumer(sub_component, consumer)
            for consumer
            in consumers
        )
        producer_records_iter: Iterator[ProducerRecord] = chain.from_iterable(
            self._parse_producer(sub_component, producer)
            for producer
            in producers
        )
        return consumer_records_iter, producer_records_iter

    def _parse(self, interfaces: list) -> Tuple[List[ConsumerRecord], List[ProducerRecord]]:
        self._validate_interfaces(interfaces)
        consumer_records: List[ConsumerRecord] = []
        producer_records: List[ProducerRecord] = []

        for interface in interfaces:
            consumer_records_iter, producer_records_iter = self._parse_interface(interface)
            consumer_records.extend(consumer_records_iter)
            producer_records.extend(producer_records_iter)

        return consumer_records, producer_records
