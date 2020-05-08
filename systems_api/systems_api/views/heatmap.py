import json
from datetime import datetime, timedelta

from pyramid.view import (
    view_config,
    view_defaults
)
from ..models import System
import pyramid.httpexceptions as exc
import psycopg2
import os


def generate_heatmap(request):
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
            res = request.dbsession.query(System).filter(System.name == row[0]).first()
            if not res:
                continue
            coords = res.coords
            heatmap.append({row[0]: {'rescues': row[1], 'coords': coords}})
        cur.close()
        conn.close()
        hj = open('heatmap.json', mode='w')
        json.dump(heatmap, hj)
        return heatmap
    except (Exception, psycopg2.Error) as error:
        print(f"Oops! {error}")


# Temporary static endpoint for API v2. V3 gets a more thorough implementation.
@view_defaults(renderer='../templates/mytemplate.jinja2')
@view_config(route_name='heatmap', renderer='json')
def heatmap(request):
    if os.path.isfile(f'heatmap.json'):
        if datetime.fromtimestamp(os.path.getmtime(f'heatmap.json')) > datetime.today() - timedelta(
                days=1):
            print("Generating new heatmap...")
            generate_heatmap(request)
        else:
                hj = open('heatmap.json', mode='r')
                heatmap = json.load(hj)
                return heatmap
    else:
        print("First run, generating heatmap...")
        generate_heatmap(request)
