import datetime, re
from copy import copy

from mock import Mock
import cx_Oracle
from sqlalchemy.sql.expression import text


def get_mock_connection(session):
    """ Mock out Oracle's Connection object with one that commits to a
    specified session object (eg, a sqlalchemy session on an in-memory db).

    :param session: object that will take the commit calls
    :returns: mock Connection object

    Eg::

        @patch(db_access_object.connection(get_mock_connection(session))
        test_foo():
           db_access_object.connection.commit()
    """
    res = Mock(spec=cx_Oracle.Connection)
    res.commit.side_effect = session.commit
    return res


def oracle_to_sqlite(sql, args):
    """ Roughly converts Oracle DML to SQLite DML 

    :param sql:     SQL 
    :type sql:      str
    :param args:    Bind params
    :type args:     dict
    :returns:       (new sql, new args)
    """
    res = sql
    res_args = copy(args)
    # We strip off schema names as SQLite doesn't easily support them
    # TODO: find a way to allow schemas in in-memory dbs.
    patterns = [
         # .. add schemas as required..
         # (r"FOO\.(\w)",r"\1"),
    ]
    for pattern, replacement in patterns:
        res = re.sub(pattern,replacement,res)

    # Handle to_dates
    for to_date in re.findall(r"to_date\([^\)]+\)", res):
        m = re.match(r"to_date\(:(\w+),\s*'([^']+)'\)", to_date)
        field = m.group(1)
        spec = m.group(2)

        # Change oracle dt spec to standard C
        for ora, c in [
            ('yyyy', '%Y'),
            ('mm', '%m'),
            ('dd', '%d'),
            ('hh24', '%H'),
            ('mi', '%M'),
            ('ss', '%S'),
          ]:
            spec = spec.replace(ora, c)

        res_args[field] = datetime.datetime.strptime(args[field], spec)
        res = res.replace(to_date, ':%s' % field)

    return res, res_args
    

def get_mock_cursor(session):
    """ Create a mock Oracle cursor that will act upon the given sqlalchemy session.

    :param session: SQLAlchemy session object
    :returns:       Mock Cursor object

    Eg::

        @patch(db_access_object.cursor(get_mock_cursor(session))
        test_foo():
            db_access_object.cursor.execute('Select Foo from Bar where Foo = :foo', {'foo': 123})
    """
    res = Mock(spec=cx_Oracle.Cursor)
    res._next_result = None

    def execute(sql, args):
        sql, args = oracle_to_sqlite(sql, args)
        #print "Mock executing: %r %r" % (sql, args)
        res._next_result = session.execute(text(sql), args)

    def fetchone():
        return res._next_result.fetchone()

    def fetchmany():
        return res._next_result.fetchall()

    res.execute.side_effect = execute
    res.fetchone.side_effect = fetchone
    res.fetchmany.side_effect = fetchmany

    return res
