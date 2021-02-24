import argparse

import sys
from pyramid.paster import bootstrap, setup_logging
from sqlalchemy.exc import OperationalError
import json
from ..models import System
import psycopg2


def generate_heatmap(dbsession, env):
    global conn
    try:
        conn = psycopg2.connect(host="192.168.100.10", database="fuelratsapi", user="fuelrats")
        cur = conn.cursor()
        cur.execute('SELECT system as "System", COUNT(system) as "Rescues" FROM "Rescues" WHERE '
                    '"deletedAt" IS NULL and position(\': false\' in "data"::json#>>\'{markedForDeletion}\')>0 '
                    'GROUP BY system ORDER BY count("system") DESC')
        rows = cur.fetchall()
        heatmap = []
        for row in rows:
            # Fetch me some system data!
            res = dbsession.query(System).filter(System.name == row[0]).first()
            if not res:
                continue
            coords = res.coords
            heatmap.append({row[0]: {'rescues': row[1], 'coords': coords}})
        cur.close()
        conn.close()
        hj = open('heatmap.json', mode='w')
        json.dump(heatmap, hj)
        print(f"New heatmap generated.")
        return
    except (Exception, psycopg2.Error) as error:
        print(f"Oops! {error}")


def parse_args(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'config_uri',
        help='Configuration file, e.g., development.ini.template',
    )
    return parser.parse_args(argv[1:])


def main(argv=sys.argv):
    args = parse_args(argv)
    setup_logging(args.config_uri)
    env = bootstrap(args.config_uri)

    try:
        with env['request'].tm:
            dbsession = env['request'].dbsession
            generate_heatmap(dbsession, bootstrap(args.config_uri))
    except OperationalError:
        print('''
Pyramid is having a problem using your SQL database.  The problem
might be caused by one of the following things:

1.  You may need to initialize your database tables with `alembic`.
    Check your README.txt for description and try to run it.

2.  Your database server may not be running.  Check that the
    database server referred to by the "sqlalchemy.url" setting in
    your "development.ini.template" file is running.
            ''')
