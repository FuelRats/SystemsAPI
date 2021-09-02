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
                 f")^2)) as Distance from populated_systems order by Distance LIMIT 5")).all()
        populated_systems = []
        for cand in candidate:
            try:
                a = numpy.array((x, y, z))
                b = numpy.array((cand.coords['x'], cand.coords['y'], cand.coords['z']))
                dist = numpy.linalg.norm(a - b)
                #print(f"{cand.name}: {dist}")

                stations = []
                station_query = request.dbsession.query(Station).filter(Station.systemId64 == cand.id64)
                if station_query:
                    for station in station_query:
                        stations.append({'name': station.name, 'type': station.type,
                                         'distance': station.distanceToArrival, 'hasOutfitting': station.haveOutfitting,
                                         'services': station.otherServices, 'hasShipyard': station.haveShipyard,
                                         'hasMarket': station.haveMarket})
                    populated_systems.append({'distance': dist, 'name': cand.name,
                                              'id64': cand.id64, 'stations': stations})
            except ValueError:
                print(
                    f"Value error: Failed for {cand.coords['x']}, {cand.coords['y']}, {cand.coords['z']}")
        return {'meta': {'name': system.name, 'type': 'nearest_populated'},
                'data': populated_systems}
    else:
        return exc.HTTPBadRequest('Missing required parameter (name or systemid64')


@view_defaults(renderer='../templates/mytemplate.jinja2')
@view_config(route_name='nearest_coords', renderer='json')
def nearest_coords(request):
    """
    Returns the nearest system in DB given a set of coordinates.
    :param request: Pyramid request object
    :return: A JSON response object
    """
    if 'x' not in request.params or 'y' not in request.params or 'z' not in request.params:
        return exc.HTTPBadRequest('Missing X, Y or Z coordinate for search.')
    try:
        x, y, z = float(request.params['x']), float(request.params['y']), float(request.params['z'])
        system = System()
        cube = 50

        candidate = request.dbsession.query(System).from_statement(
            text(f"SELECT *, (sqrt((cast(systems.coords->>'x' AS FLOAT) - {x}"
                 f")^2 + (cast(systems.coords->>'y' AS FLOAT) - {y}"
                 f")^2 + (cast(systems.coords->>'z' AS FLOAT) - {z}"
                 f")^2)) AS Distance FROM systems JOIN stars ON systems.id64 = stars.\"systemId64\""
                 f" WHERE cast(systems.coords->>'x' AS FLOAT) BETWEEN {str(float(x)-cube)} AND {str(float(x)+cube)}"
                 f" AND cast(systems.coords->>'y' AS FLOAT) BETWEEN {str(float(y)-cube)} AND {str(float(y)+cube)}"
                 f" AND cast(systems.coords->>'z' as FLOAT)"
                 f" BETWEEN {str(float(z)-cube)} AND {str(float(z)+cube)} order by Distance LIMIT 1")).one()
        a = numpy.array((x, y, z))
        b = numpy.array((candidate.coords['x'], candidate.coords['y'], candidate.coords['z']))
        dist = numpy.linalg.norm(a - b)

        return {'meta': {'name': system.name, 'type': 'nearest_coords'},
                'data': {'distance': dist, 'name': candidate.name, 'id64': candidate.id64}}

    except NoResultFound:
        return {'meta': {'name': system.name, 'type': 'nearest_scoopable'},
                'error': 'No scoopable systems found.'}
    except ValueError:
        return exc.HTTPBadRequest('Malformed request data.')


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
                 f")^2)) AS Distance FROM systems JOIN stars ON systems.id64 = stars.\"systemId64\""
                 f" WHERE cast(systems.coords->>'x' AS FLOAT) BETWEEN {str(float(x)-cube)} AND {str(float(x)+cube)}"
                 f" AND cast(systems.coords->>'y' AS FLOAT) BETWEEN {str(float(y)-cube)} AND {str(float(y)+cube)}"
                 f" AND cast(systems.coords->>'z' as FLOAT)"
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
