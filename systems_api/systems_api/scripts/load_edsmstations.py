import bigjson
import gzip
import os
import sys
from datetime import datetime, timedelta

import transaction
import requests

from pyramid.paster import (
    get_appsettings,
    setup_logging,
)
from pyramid.scripts.common import parse_vars
from systems_api.models import (
    get_engine,
    get_session_factory,
    get_tm_session,
)

from systems_api.models.station import Station


def usage(argv):
    cmd = os.path.basename(argv[0])
    print('usage: %s <config_uri> [var=value]\n'
          '(example: "%s development.ini")' % (cmd, cmd))
    sys.exit(1)


def main(argv=sys.argv):
    if len(argv) < 2:
        usage(argv)
    config_uri = argv[1]
    options = parse_vars(argv[2:])
    setup_logging(config_uri)
    settings = get_appsettings(config_uri, name='main', options=options)
    engine = get_engine(settings)
    session_factory = get_session_factory(engine)
    session = get_tm_session(session_factory, transaction.manager)

    if os.path.isfile('stations.json.gz'):
        if datetime.fromtimestamp(os.path.getmtime('stations.json')) > datetime.today() - timedelta(days=7):
            print("Using cached stations.json.gz")
    else:
        print("Downloading stations.json from EDSM.net...")
        r = requests.get("	https://www.edsm.net/dump/stations.json.gz", stream=True)
        with open('stations.json.gz', 'wb') as f:
            for chunk in r.iter_content(chunk_size=4096):
                if chunk:
                    f.write(chunk)
        print("Saved stations.json. Converting JSONL to SQL.")

    with gzip.open('stations.json.gz', 'rb') as infile:
        counter = 0
        j = bigjson.load(infile)
        for element in j:
            if element['type'] == 'Fleet Carrier':
                continue
            station = Station(id64=element['id'], marketId=element['marketId'], type=element['type'],
                              name=element['name'], distanceToArrival=element['distanceToArrival'],
                              allegiance=element['allegiance'], government=element['government'],
                              economy=element['economy'], haveMarket=element['haveMarket'],
                              haveShipyard=element['haveShipyard'], haveOutfitting=element['haveOutfitting'],
                              otherServices=element['otherServices'].to_python(),
                              updateTime=element['updateTime']['information'],
                              systemId64=element['systemId64'], systemName=element['systemName']
                              )
            session.add(station)
            counter += 1
            if counter >= 1000:
                transaction.commit()
                counter = 0

    print("Creating indexes...")
    session.execute("CREATE INDEX index_stations_systemid_btree ON stations(\"systemId\")")
    transaction.commit()
    session.execute("CREATE INDEX index_stations_btree ON stations(id)")
    transaction.commit()
    print("Done!")
