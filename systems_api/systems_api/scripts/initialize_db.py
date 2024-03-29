import argparse
import os
import sys
from bz2 import BZ2Decompressor
from datetime import datetime, timedelta
from urllib.parse import urljoin
import requests
import wget as wget
from pyramid.paster import bootstrap, setup_logging
from sqlalchemy.exc import OperationalError

from .. import models


def setup_models(dbsession, env):
    """
    Add or update models / fixtures in the database.

    """
    permit_systems = [
        10477373803,
        301958431924,
        1733052863178,
        670954497449,
        1006909786467,
        633675420378,
        663329196387,
        358864622282,
        7268561135001,
        5068732442025,
        3107710898898,
        164098653,
        972566792555,
        1384883652971,
        1109989017963,
        44837112163,
        670685799809,
        121569805492,
        670685996457,
        9467047454129,
        869470816603,
        1350523947317,
        633675453138,
        869454039395,
        251012319595,
        938207070571,
        2415675853163,
        1350523947371,
    ]
    snowflake_permits = {
        319715002691: "HIP22460 System",
        40553617967984: "Pilots' Federation District",
        10494151019: "Beta Hydri",
        3107576615650: "CQC Home World",
        1213084977515: "Pilots' Federation District",
        7268292568505: "Pilots' Federation District",
        633608278738: "LTT 198",
        2870246057401: "Pilots' Federation District",
        22962505665400: "Pilots' Federation District",
        5370319620984: "Pilots' Federation District",
        1733187048154: "Pilots' Federation District",
        3932277478106: "Founders World",
        5369245879160: "Pilots' Federation District",
        22961431923576: "Pilots' Federation District",
        22961431923568: "Pilots' Federation District"
    }
    print("Adding permit systems...")
    for permit in permit_systems:
        psystem = models.permits.Permits(id64=permit)
        dbsession.add(psystem)
    for permit, snowflake in snowflake_permits.items():
        psystem = models.permits.Permits(id64=permit, permit_name=snowflake)
        dbsession.add(psystem)
    print("Adding default landmarks...")
    lm = models.landmark.Landmark(name="Beagle Point", x=-1111.56, y=-134.22, z=65269.75, soi=12000.0)
    dbsession.add(lm)
    lm = models.landmark.Landmark(name="Boewnst KS-S c20-959 (Polo Harbour)", x=-6195.47, y=-140.28,
                                  z=16462.06, soi=1100.0)
    dbsession.add(lm)
    lm = models.landmark.Landmark(name="Colonia", x=-9530.5, y=-910.28, z=19808.12)
    dbsession.add(lm)
    lm = models.landmark.Landmark(name="Fuelum", x=52, y=-52.66, z=49.81)
    dbsession.add(lm)
    lm = models.landmark.Landmark(name="Gru Hypue KS-T d3-31 (Gagarin Gate)", x=-4990.84, y=-935.72,
                                  z=13387.16, soi=1100.0)
    dbsession.add(lm)
    lm = models.landmark.Landmark(name="Maia", x=-81.78, y=-149.44, z=-343.38, soi=250.0)
    dbsession.add(lm)
    lm = models.landmark.Landmark(name="Rodentia", x=-9530.53, y=-907.25, z=19787.38, soi=4500.0)
    dbsession.add(lm)
    lm = models.landmark.Landmark(name="Rohini", x=-3374.81, y=-47.81, z=6912.25, soi=1100.0)
    dbsession.add(lm)
    lm = models.landmark.Landmark(name="Sagittarius A*", x=25.22, y=-20.91, z=25899.97, soi=6500)
    dbsession.add(lm)
    lm = models.landmark.Landmark(name="Skaudai CH-B d14-34 (Sacaqawea Space Port)", x=-5481.84, y=-579.16,
                                  z=10429.94, soi=1100)
    dbsession.add(lm)
    lm = models.landmark.Landmark(name="Omega Sector VE-Q b5-15 (Omega Mining Operation)", x=-1444.3125, y=-85.8125,
                                  z=5319.9375, soi=500)
    dbsession.add(lm)
    lm = models.landmark.Landmark(name="Sol", x=0, y=0, z=0)
    dbsession.add(lm)
    settings = env['request'].registry.settings
    filelist = ['systemsWithCoordinates', 'systemsPopulated', 'stars', 'planets']
    if 'stardb_host' not in settings:
        print("Your config does not specify a host for downloading E:D galaxy map data. You will have to"
              "download and inject the data manually into the database.")
        return
    host = settings['stardb_host']
    #host = "https://downloads.spansh.co.uk"
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
            url = urljoin(host, f"{file}.csv.bz2")
            print(f"\nDownloading {url}...")
            wget.download(url, f"{file}.csv.bz2")
    for file in neededfiles:
        with open(f'{file}.csv', 'wb') as outfile, open(f'{file}.csv.bz2', 'rb') as infile:
            print(f"\nDecompressing {file}.csv.bz2...")
            decompressor = BZ2Decompressor()
            for data in iter(lambda: infile.read(100*1024), b''):
                outfile.write(decompressor.decompress(data))
    print("Complete!")
    print("You now need to inject these CSV files into your postgres database using the following command in psql:")
    print("COPY <table> from <csvfile.csv> WITH CSV HEADER QUOTE AS '\"' ESCAPE AS '\\' DELIMITER E',';")


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
            setup_models(dbsession, bootstrap(args.config_uri))
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
