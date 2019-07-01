from collections import Counter
from typing import List
from psycopg2.extras import execute_values
from psycopg2.sql import SQL, Literal
from psycopg2.errors import UniqueViolation, RaiseException

from service.util.parse_interfaces import ConsumerRecord, ProducerRecord

SQL_LOCK_EXCLUSIVE_CONSUMERS = 'LOCK TABLE consumers IN EXCLUSIVE MODE;'

SQL_DELETE_CONSUMERS = '''
DELETE FROM consumers
WHERE component={component}
AND (subcomponent, host, itype, iprimary, isecondary, itertiary, optional)
NOT IN (VALUES %s);
'''

SQL_DELETE_PRODUCERS = '''
DELETE FROM producers
WHERE component={component}
AND (subcomponent, host, itype, iprimary, isecondary, itertiary, deprecated)
NOT IN (VALUES %s);
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


class InterfaceEntryDuplication(Exception):
    pass

class InterfaceEntryConflict(Exception):
    pass

def _guarantee_consumer_uniqueness(consumers:List[ConsumerRecord]):
    expected_unique_consumers = [
        (c.sub_component, c.interface_host, c.interface_type, c.primary, c.secondary, c.tertiary)
        for c
        in consumers
    ]
    non_unique_consumers = [item for item, count in Counter(expected_unique_consumers).items() if count > 1]
    if non_unique_consumers:
        raise InterfaceEntryDuplication(
            f'The following consumer was specified multiple times: {non_unique_consumers[0]}')


def _guarantee_producer_uniqueness(producers:List[ProducerRecord]):
    expected_unique_producers = [
        (p.sub_component, p.interface_host, p.interface_type, p.primary, p.secondary, p.tertiary)
        for p
        in producers
    ]
    non_unique_producers = [item for item, count in Counter(expected_unique_producers).items() if count > 1]
    if non_unique_producers:
        raise InterfaceEntryDuplication(
            f'The following producer was specified multiple times: {non_unique_producers[0]}')


def set_interface(connection, component: str, consumers:List[ConsumerRecord], producers:List[ProducerRecord]):
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
            execute_values(cursor, sql_delete_consumers, consumers_for_db)
            execute_values(cursor, sql_delete_producers, producers_for_db)
            # insert producers before inserting consumers
            execute_values(cursor, sql_insert_producers, producers_for_db)
            execute_values(cursor, sql_insert_consumers, consumers_for_db)
        connection.commit()
    except UniqueViolation as e:
        raise InterfaceEntryDuplication(f'The interface specification contains one value multiple times: {e}')
    except RaiseException as e:
        raise InterfaceEntryConflict(f'Error: {e.pgerror.splitlines()[0]}')
