from pyramid.view import (
    view_config,
    view_defaults
)
from sqlalchemy import text, func
from ..models import System, Permits, Carrier, Star, PopulatedSystem
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
    if 'systemid64' in request.params:
        try:
            system = request.dbsession.query(System).filter(System.id64 == request.params['systemid64']).one()
            x, y, z = system.coords['x'], system.coords['y'], system.coords['z']
            print(f"X: {x} Y: {y} Z: {z}")
            cube = 200
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
                return {'meta': {'name': candidate.name, 'type': 'nearest_populated'},
                        'data': {'distance': dist, 'name': candidate.name, 'id64': candidate.id64}}
            except ValueError:
                print(
                    f"Value error: Failed for {candidate.coords['x']}, {candidate.coords['y']}, {candidate.coords['z']}")
        except NoResultFound:
            return exc.HTTPBadRequest('SystemID64 not found.')
        except MultipleResultsFound:
            return exc.HTTPServerError('Multiple rows matching system ID found. This should not happen.')


@view_defaults(renderer='../templates/mytemplate.jinja2')
@view_config(route_name='nearest_scoopable', renderer='json')
def nearest_scoopable(request):
    """
    Returns the nearest scoopable system to a given system. Supports being asked with either a
    systemID passed as systemid64, or searching by name with the name parameter.
    :param request: The Pyramid request object
    :return: A JSON response
    """
    if 'systemid64' in request.params:
        try:
            system = request.dbsession.query(System).filter(System.id64 == request.params['systemid64']).one()
            x, y, z = system.coords['x'], system.coords['y'], system.coords['z']
            cube = 200
            candidates = request.dbsession.query(System). \
                filter(and_(System.coords['x'].as_float().between((x - cube), (x + cube)),
                            System.coords['y'].as_float().between((y - cube), (y + cube)),
                            System.coords['z'].as_float().between((z - cube), (z + cube)))).join(Star).all()
            results = []
            for candidate in candidates:
                for star in candidate.stars:
                    try:
                        if star.isScoopable is True:
                            a = numpy.array((x, y, z))
                            b = numpy.array((candidate.coords['x'], candidate.coords['y'], candidate.coords['z']))
                            dist = numpy.linalg.norm(a - b)
                            results.append((candidate, dist))
                    except ValueError:
                        print(
                            f"Value error: Failed for {candidate.coords['x']}, {candidate.coords['y']}, {candidate.coords['z']}")
            res = sorted(results, key=lambda cand: cand[1])
            return {'meta': {'name': res[0][0].name, 'type': 'nearest_scoopable'},
                    'data': {'distance': res[0][1], 'name': res[0][0].name, 'id64': res[0][0].id64}}
        except NoResultFound:
            return exc.HTTPBadRequest('SystemID64 not found.')
        except MultipleResultsFound:
            return exc.HTTPServerError('Multiple rows matching system ID found. This should not happen.')
