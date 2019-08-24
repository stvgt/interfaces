from collections import Counter, defaultdict
from typing import List

import psycopg2
from psycopg2.extras import execute_values
from psycopg2.sql import SQL, Literal
from psycopg2.errors import UniqueViolation, RaiseException

from service.util.parse_interfaces import (
    Component,
    ConsumerRecord,
    ProducerRecord,
)

SQL_LOCK_EXCLUSIVE_CONSUMERS = 'LOCK TABLE consumers IN EXCLUSIVE MODE;'

SQL_DELETE_CONSUMERS = '''
DELETE FROM consumers
WHERE component={component}
'''
SQL_CONSUMERS_NOT_IN = '''
AND (subcomponent, host, itype, iprimary, isecondary, itertiary, optional) NOT IN (VALUES %s)
'''

SQL_DELETE_PRODUCERS = '''
DELETE FROM producers
WHERE component={component}
'''

SQL_PRODUCERS_NOT_IN = '''
AND (subcomponent, host, itype, iprimary, isecondary, itertiary, deprecated) NOT IN (VALUES %s)
'''

SQL_INSERT_CONSUMERS = '''
INSERT INTO consumers (component, subcomponent, host, itype, iprimary, isecondary, itertiary, optional)
(
    SELECT {component}, v.subcomponent, v.host, v.itype, v.iprimary, v.isecondary, v.itertiary, v.optional
    FROM (VALUES %s) as v (subcomponent, host, itype, iprimary, isecondary, itertiary, optional)
    WHERE (v.subcomponent, v.host, v.itype, v.iprimary, v.isecondary, v.itertiary, v.optional)
    NOT IN (
        SELECT c.subcomponent, c.host, c.itype, c.iprimary, c.isecondary, c.itertiary, c.optional
        FROM consumers as c
        WHERE c.component = {component}
    )
);
'''

SQL_INSERT_PRODUCERS = '''
INSERT INTO producers (component, subcomponent, host, itype, iprimary, isecondary, itertiary, deprecated)
(
    SELECT {component}, v.subcomponent, v.host, v.itype, v.iprimary, v.isecondary, v.itertiary, v.deprecated
    FROM (VALUES %s) as v (subcomponent, host, itype, iprimary, isecondary, itertiary, deprecated)
    WHERE (v.subcomponent, v.host, v.itype, v.iprimary, v.isecondary, v.itertiary, v.deprecated)
    NOT IN (
        SELECT p.subcomponent, p.host, p.itype, p.iprimary, p.isecondary, p.itertiary, p.deprecated
        FROM producers as p
        WHERE p.component = {component}
    )
);
'''

SQL_GET_CONSUMERS = '''
SELECT
    c.component as component,
    c.subcomponent as sub_component,
    c.host as interface_host,
    c.itype as interface_type,
    c.iprimary as primary,
    c.isecondary as secondary,
    c.itertiary as tertiary,
    c.optional as optional
FROM consumers as c;
'''

SQL_GET_PRODUCERS = '''
SELECT
    p.component as component,
    p.subcomponent as sub_component,
    p.host as interface_host,
    p.itype as interface_type,
    p.iprimary as primary,
    p.isecondary as secondary,
    p.itertiary as tertiary,
    p.deprecated as deprecated
FROM producers as p;
'''


class InterfaceEntryDuplication(Exception):
    pass


class InterfaceEntryConflict(Exception):
    pass


def _guarantee_consumer_uniqueness(consumers: List[ConsumerRecord]) -> None:
    expected_unique_consumers = [
        (c.sub_component, c.interface_host, c.interface_type, c.primary, c.secondary, c.tertiary)
        for c
        in consumers
    ]
    non_unique_consumers = [item for item, count in Counter(expected_unique_consumers).items() if count > 1]
    if non_unique_consumers:
        raise InterfaceEntryDuplication(
            f'The following consumer was specified multiple times: {non_unique_consumers[0]}')


def _guarantee_producer_uniqueness(producers: List[ProducerRecord]) -> None:
    expected_unique_producers = [
        (p.sub_component, p.interface_host, p.interface_type, p.primary, p.secondary, p.tertiary)
        for p
        in producers
    ]
    non_unique_producers = [item for item, count in Counter(expected_unique_producers).items() if count > 1]
    if non_unique_producers:
        raise InterfaceEntryDuplication(
            f'The following producer was specified multiple times: {non_unique_producers[0]}')


def set_interface(connection, component: str, consumers: List[ConsumerRecord], producers: List[ProducerRecord]) -> None:
    _guarantee_consumer_uniqueness(consumers)
    _guarantee_producer_uniqueness(producers)

    consumers_for_db = [
        (c.sub_component, c.interface_host, c.interface_type, c.primary, c.secondary, c.tertiary, c.optional)
        for c
        in consumers
    ]
    producers_for_db = [
        (p.sub_component, p.interface_host, p.interface_type, p.primary, p.secondary, p.tertiary, p.deprecated)
        for p
        in producers
    ]

    try:
        sql_delete_consumers = SQL(SQL_DELETE_CONSUMERS).format(component=Literal(component))
        sql_delete_producers = SQL(SQL_DELETE_PRODUCERS).format(component=Literal(component))
        sql_insert_consumers = SQL(SQL_INSERT_CONSUMERS).format(component=Literal(component))
        sql_insert_producers = SQL(SQL_INSERT_PRODUCERS).format(component=Literal(component))

        with connection.cursor() as cursor:
            # delete consumers before deleting producers
            cursor.execute(SQL_LOCK_EXCLUSIVE_CONSUMERS)
            if consumers_for_db:
                execute_values(
                    cursor,
                    sql_delete_consumers + SQL(SQL_CONSUMERS_NOT_IN),
                    consumers_for_db,
                    page_size=len(consumers_for_db),  # sending chunkwise would delete all elements not in chunk
                )
            else:
                cursor.execute(sql_delete_consumers)
            if producers_for_db:
                execute_values(
                    cursor,
                    sql_delete_producers + SQL(SQL_PRODUCERS_NOT_IN),
                    producers_for_db,
                    page_size=len(producers_for_db),  # sending chunkwise would delete all elements not in chunk
                )
            else:
                cursor.execute(sql_delete_producers)
            # insert producers before inserting consumers
            execute_values(cursor, sql_insert_producers, producers_for_db)
            execute_values(cursor, sql_insert_consumers, consumers_for_db)
        connection.commit()
    except UniqueViolation as e:
        raise InterfaceEntryDuplication(f'The interface specification contains one value multiple times: {e}')
    except RaiseException as e:
        raise InterfaceEntryConflict(f'Error: {e.pgerror.splitlines()[0]}')


def get_components(connection) -> List[Component]:
    with connection.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
        cursor.execute(SQL_GET_CONSUMERS)
        consumers = cursor.fetchall()
        cursor.execute(SQL_GET_PRODUCERS)
        producers = cursor.fetchall()

    consumers_by_component = defaultdict(list)
    for c in consumers:
        consumers_by_component[c['component']].append(ConsumerRecord(**{k: v for k, v in c.items() if k != 'component'}))
    producers_by_component = defaultdict(list)
    for p in producers:
        producers_by_component[p['component']].append(ProducerRecord(**{k: v for k, v in p.items() if k != 'component'}))

    components = set(consumers_by_component.keys()).union(producers_by_component.keys())

    return [
        Component(
            name=component,
            consumers=consumers_by_component.get(component, []),
            producers=producers_by_component.get(component, []),
        )
        for component
        in components
    ]
