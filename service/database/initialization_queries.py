SQL_INIT_TABLES_AND_TRIGGERS = '''
    CREATE TABLE consumers
    (
        component TEXT NOT NULL,
        subcomponent TEXT NOT NULL,
        host TEXT NOT NULL,
        itype TEXT NOT NULL,
        iprimary TEXT NOT NULL,
        isecondary TEXT NOT NULL,
        itertiary TEXT NOT NULL,
        optional BOOLEAN NOT NULL,
        unique (component, subcomponent, host, itype, iprimary, isecondary, itertiary)
    );

    CREATE TABLE producers
    (
        component TEXT NOT NULL,
        subcomponent TEXT NOT NULL,
        host TEXT NOT NULL,
        itype TEXT NOT NULL,
        iprimary TEXT NOT NULL,
        isecondary TEXT NOT NULL,
        itertiary TEXT NOT NULL,
        deprecated BOOLEAN NOT NULL,
        unique (component, subcomponent, host, itype, iprimary, isecondary, itertiary)    
    );

    CREATE OR REPLACE FUNCTION ensure_producer_exists()
    RETURNS TRIGGER AS $producers_check$
    BEGIN
        IF (
            NEW.optional
            OR
            EXISTS(
                SELECT 1
                FROM producers as other
                WHERE other.host = NEW.host
                AND other.itype = NEW.itype
                AND other.iprimary = NEW.iprimary
                AND other.isecondary = NEW.isecondary
                AND other.itertiary = NEW.itertiary
            )
        ) THEN
            RETURN NEW;
        END IF;
        RAISE EXCEPTION 'no producer for interface "%" "%" "%" "%" "%"', 
            NEW.host, NEW.itype, NEW.iprimary, NEW.isecondary, NEW.itertiary;
    END;
    $producers_check$ LANGUAGE plpgsql;
    
    CREATE OR REPLACE FUNCTION ensure_no_consumer_exists()
    RETURNS TRIGGER AS $consumers_check$
    BEGIN
        IF (
            EXISTS(
                SELECT 1
                FROM consumers as other
                WHERE other.host = OLD.host
                AND other.itype = OLD.itype
                AND other.iprimary = OLD.iprimary
                AND other.isecondary = OLD.isecondary
                AND other.itertiary = OLD.itertiary
                AND other.optional = FALSE
            )    
        ) THEN
            IF (
                NOT EXISTS(
                    SELECT 1
                    FROM producers as other
                    WHERE other.host = OLD.host
                    AND other.itype = OLD.itype
                    AND other.iprimary = OLD.iprimary
                    AND other.isecondary = OLD.isecondary
                    AND other.itertiary = OLD.itertiary
                    AND other.component <> OLD.component
                    AND other.subcomponent <> OLD.subcomponent
                )    
            ) THEN
                RAISE EXCEPTION 'no other producer for used interface "%" "%" "%" "%" "%"', 
                    OLD.host, OLD.itype, OLD.iprimary, OLD.isecondary, OLD.itertiary;
            END IF;    
        END IF;
        RETURN OLD;
    END;
    $consumers_check$ LANGUAGE plpgsql;
    
    CREATE TRIGGER producers_check BEFORE INSERT ON consumers
        FOR each row execute procedure ensure_producer_exists();
    
    CREATE TRIGGER consumers_check BEFORE DELETE ON producers
        FOR each row execute procedure ensure_no_consumer_exists();
        
    CREATE INDEX consumers_component on consumers (component);
    CREATE INDEX producers_component on producers (component);
'''

SQL_DROP_ALL = '''
    DROP INDEX IF EXISTS consumers_component;
    DROP INDEX IF EXISTS producers_component;
    DROP TRIGGER IF EXISTS consumers_check ON producers;
    DROP TRIGGER IF EXISTS producers_check ON consumers;
    DROP FUNCTION If EXISTS ensure_no_consumer_exists();
    DROP FUNCTION IF EXISTS ensure_producer_exists();
    DROP TABLE IF EXISTS consumers;
    DROP TABLE IF EXISTS producers;
'''
