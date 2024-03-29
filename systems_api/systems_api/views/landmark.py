from pyramid.view import (
    view_config,
    view_defaults
)
from sqlalchemy import text
from ..models import Landmark, System
from pyramid.httpexceptions import HTTPBadRequest


@view_defaults(renderer='../templates/mytemplate.jinja2')
@view_config(route_name='landmark', renderer='json')
def landmark(request):
    """
    Gets distance to nearest landmark for given system, and allows listing and adding new landmarks.
    :param request: The Pyramid request object
    :return: A JSON response
    """

    if "list" in request.params:
        result = request.dbsession.query(Landmark)
        landmarks = []
        for row in result:
            landmarks.append({'name': row.name, 'x': row.x, 'y': row.y,
                              'z': row.z, 'soi': row.soi})
        return {'meta': {'count': len(landmarks)}, 'landmarks': landmarks}
    if "add" in request.params:
        if "name" not in request.params:
            return HTTPBadRequest(detail="No name parameter supplied.")
        name = str(request.params['name'])
        result = request.dbsession.query(System).filter(System.name == name).limit(1)
        result2 = request.dbsession.query(Landmark)
        if name in result2:
            return {'meta': {'error': 'System is already a landmark.'}}
        if result.rowcount > 0:
            for row in result:
                x = float(row['coords']['x'])
                y = float(row['coords']['y'])
                z = float(row['coords']['z'])
                sysname = str(row['name'])
            newlandmark = Landmark(name=sysname, x=x, y=y, z=z,
                                   soi=requests.params['soi'] if 'soi' in request.params else None)
            request.dbsession.add(newlandmark)
            return {'meta': {'success': 'System added as a landmark.'}}
        else:
            return {'meta': {'error': 'System not found.'}}
    if "name" not in request.params:
        return HTTPBadRequest(detail="No name parameter supplied.")
    name = str(request.params['name'])
    result = request.dbsession.query(System).filter(System.name == name).limit(1)
    if result.count() > 0:
        rname = None
        for row in result:
            print(f"Coords: {row.coords}")
            x = float(row.coords['x'])
            y = float(row.coords['y'])
            z = float(row.coords['z'])
            rname = str(row.name)
        if name.lower() != rname.lower():
            return HTTPBadRequest('System name ambiguous or not found.')
        sql = text(f"SELECT *,(sqrt((cast(landmarks.x AS FLOAT) - {x}"
                   f")^2 + (cast(landmarks.y AS FLOAT) - {y}"
                   f")^2 + (cast(landmarks.z AS FLOAT) - {z}"
                   f")^2)) as DISTANCE from landmarks ORDER BY DISTANCE;")
        result = request.dbsession.execute(sql)
        candidates = []
        for row in result:
            if row['soi'] is None or row['soi'] > row['distance'] or row['soi'] == 0.0:
                candidates.append({'name': row['name'], 'distance': row['distance']})
    else:
        return {'meta': {'error': 'System not found.'}}
    return {'meta': {'name': name},
            'landmarks': candidates}
