import argparse
import os
import sys
from bz2 import BZ2Decompressor
from datetime import datetime, timedelta

import requests
from pyramid.paster import bootstrap, setup_logging
from sqlalchemy.exc import OperationalError

from .. import models


def setup_models(dbsession, env):
    """
    Add or update models / fixtures in the database.

    """
    model = models.mymodel.MyModel(name='one', value=1)
    dbsession.add(model)
    settings = env['registry']['settings']
    filelist = ['systemsWithCoordinates', 'systemsWithoutCoordinates', 'systemsPopulated', 'stars', 'bodies']
    if 'stardb_host' not in settings:
        print("Your config does not specify a host for downloading E:D galaxy map data. You will have to"
              "inject the data manually into the database.")
        return
    host = settings['stardb_host']
    neededfiles = []
    for file in filelist:
        if os.path.isfile(f'{file}.csv.bz2'):
            if datetime.fromtimestamp(os.path.getmtime(f'{file}.csv.bz2')) > datetime.today() - timedelta(
                    days=7):
                print(f"Using cached {file}.csv.bz2")
            else:
                print(f"Need to download {file} (Too old)")
                neededfiles.append(file)
        else:
            print(f"Need to download {file} (Missing)")
            neededfiles.append(file)
    if neededfiles:
        for file in neededfiles:
            print(f"Downloading {file}.csv from Spansh...")
            r = requests.get(f"{host}/{file}.csv.bz2", stream=True)
        with open('{file}.csv.bz2', 'wb') as f:
            for chunk in r.iter_content(chunk_size=4096):
                if chunk:
                    f.write(chunk)
    print("Decompressing files...")
    with open('systemsWithCoordinates.csv', 'wb') as outfile, open('systemsWithCoordinates.csv.bz2', 'rb') as infile:
        decompressor = BZ2Decompressor()
        for data in iter(lambda : infile.read(100*1024), b''):
            outfile.write(decompressor.decompress(data))


def parse_args(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'config_uri',
        help='Configuration file, e.g., development.ini',
    )
    return parser.parse_args(argv[1:])


def main(argv=sys.argv):
    args = parse_args(argv)
    setup_logging(args.config_uri)
    env = bootstrap(args.config_uri)

    try:
        with env['request'].tm:
            dbsession = env['request'].dbsession
            setup_models(dbsession, env)
    except OperationalError:
        print('''
Pyramid is having a problem using your SQL database.  The problem
might be caused by one of the following things:

1.  You may need to initialize your database tables with `alembic`.
    Check your README.txt for description and try to run it.

2.  Your database server may not be running.  Check that the
    database server referred to by the "sqlalchemy.url" setting in
    your "development.ini" file is running.
            ''')
