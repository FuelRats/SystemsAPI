from pyramid.view import (
    view_config,
    view_defaults
)
from sqlalchemy import text, func
from ..models import System, Permits, Carrier, Star, PopulatedSystem, Station
import pyramid.httpexceptions as exc
from ..utils.util import checkpermitname, resultstocandidates
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from sqlalchemy import and_, text
import numpy


@view_defaults(renderer='../templates/mytemplate.jinja2')
@view_config(route_name='nearest_populated', renderer='json')
def nearest_populated(request):
    """
    Returns the nearest populated system to a given system. Supports being asked with either a
    systemID passed as systemid64, or searching by name with the name parameter.
    :param request: The Pyramid request object
    :return: A JSON response
    """
    x, y, z = 0.0, 0.0, 0.0
    system = System()
    if 'systemid64' in request.params:
        try:
            system = request.dbsession.query(System).filter(System.id64 == request.params['systemid64']).one()
            x, y, z = system.coords['x'], system.coords['y'], system.coords['z']
        except NoResultFound:
            return exc.HTTPBadRequest('SystemID64 not found.')
        except MultipleResultsFound:
            return exc.HTTPServerError('Multiple rows matching system ID found. This should not happen.')

    elif 'name' in request.params:
        if len(request.params['name']) < 3:
            return exc.HTTPBadRequest('Name too short. (Must be at least 3 characters)')
        try:
            system = request.dbsession.query(System).filter(System.name.ilike(request.params['name'])).one()
            x, y, z = system.coords['x'], system.coords['y'], system.coords['z']
        except NoResultFound:
            return exc.HTTPBadRequest('System not found.')
        except MultipleResultsFound:
            return exc.HTTPServerError('Multiple rows matching system found. Ensure system is unambiguous.')

        candidate = request.dbsession.query(PopulatedSystem).from_statement(
            text(f"SELECT *, (sqrt((cast(populated_systems.coords->>'x' AS FLOAT) - {x}"
                 f")^2 + (cast(populated_systems.coords->>'y' AS FLOAT) - {y}"
                 f")^2 + (cast(populated_systems.coords->>'z' AS FLOAT) - {z}"
                 f")^2)) as Distance from populated_systems order by Distance LIMIT 1")).one()
        try:
            a = numpy.array((x, y, z))
            b = numpy.array((candidate.coords['x'], candidate.coords['y'], candidate.coords['z']))
            dist = numpy.linalg.norm(a - b)
            print(f"{candidate.name}: {dist}")
            stations = []
            station_query = request.dbsession.query(Station).filter(Station.systemId64 == candidate.id64)
            if station_query:
                for station in station_query:
                    stations.append({'name': station.name, 'type': station.type,
                                     'distance': station.distanceToArrival, 'hasOutfitting': station.haveOutfitting,
                                     'services': station.otherServices, 'hasShipyard': station.haveShipyard,
                                     'hasMarket': station.haveMarket})
            return {'meta': {'name': system.name, 'type': 'nearest_populated'},
                    'data': {'distance': dist, 'name': candidate.name, 'id64': candidate.id64, 'stations': stations}}
        except ValueError:
            print(
                f"Value error: Failed for {candidate.coords['x']}, {candidate.coords['y']}, {candidate.coords['z']}")
    else:
        return exc.HTTPBadRequest('Missing required parameter (name or systemid64')


@view_defaults(renderer='../templates/mytemplate.jinja2')
@view_config(route_name='nearest_scoopable', renderer='json')
def nearest_scoopable(request):
    """
    Returns the nearest scoopable system to a given system. Supports being asked with either a
    systemID passed as systemid64, or searching by name with the name parameter.
    :param request: The Pyramid request object
    :return: A JSON response
    """
    x, y, z = 0.0, 0.0, 0.0
    system = System()
    cube = 50
    if 'systemid64' in request.params:
        try:
            system = request.dbsession.query(System).filter(System.id64 == request.params['systemid64']).one()
            x, y, z = system.coords['x'], system.coords['y'], system.coords['z']
        except NoResultFound:
            return exc.HTTPBadRequest('SystemID64 not found.')
        except MultipleResultsFound:
            return exc.HTTPServerError('Multiple rows matching system ID found. This should not happen.')
    elif 'name' in request.params:
        if len(request.params['name']) < 3:
            return exc.HTTPBadRequest('Search term too short (Minimum 3 characters)')
        try:
            system = request.dbsession.query(System).filter(System.name.ilike(request.params['name'])).one()
            x, y, z = system.coords['x'], system.coords['y'], system.coords['z']
        except NoResultFound:
            return exc.HTTPBadRequest('System not found.')
        except MultipleResultsFound:
            return exc.HTTPServerError('Multiple rows matching system name found. This should not happen.')
    else:
        return exc.HTTPBadRequest('Missing required parameter (name or systemid64)')

    for star in request.dbsession.query(Star).filter(Star.systemId64 == system.id64):
        if star.isScoopable:
            # Silly wabbit, you are scoopable.
            return {'meta': {'name': system.name, 'type': 'nearest_scoopable'},
                    'data': {'distance': 0.0, 'name': system.name, 'id64': system.id64}}
    try:
        candidate = request.dbsession.query(System).from_statement(
            text(f"SELECT *, (sqrt((cast(systems.coords->>'x' AS FLOAT) - {x}"
                 f")^2 + (cast(systems.coords->>'y' AS FLOAT) - {y}"
                 f")^2 + (cast(systems.coords->>'z' AS FLOAT) - {z}"
                 f")^2)) as Distance from systems JOIN stars ON systems.id64 = stars.\"systemId64\" "
                 f"where cast(systems.coords->>'x' AS FLOAT) BETWEEN {str(float(x)-cube)} AND {str(float(x)+cube)}"
                 f" AND cast(systems.coords->>'y' AS FLOAT) BETWEEN {str(float(y)-cube)} AND {str(float(y)+cube)} AND cast(systems.coords->>'z' as FLOAT)"
                 f" BETWEEN {str(float(z)-cube)} AND {str(float(z)+cube)} order by Distance LIMIT 1")).one()
        a = numpy.array((x, y, z))
        b = numpy.array((candidate.coords['x'], candidate.coords['y'], candidate.coords['z']))
        dist = numpy.linalg.norm(a - b)

        return {'meta': {'name': system.name, 'type': 'nearest_scoopable'},
                'data': {'distance': dist, 'name': candidate.name, 'id64': candidate.id64}}
    except NoResultFound:
        return {'meta': {'name': system.name, 'type': 'nearest_scoopable'},
                'error': 'No scoopable systems found.'}
    except MultipleResultsFound:
        return exc.HTTPServerError('Multiple results from a query that should return only one hit. This is Wrong.')
