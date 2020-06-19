from pyramid.view import (
    view_config,
    view_defaults
)

from sqlalchemy import text, func
from ..models import System, PopulatedSystem, Permits
from ..utils.util import checkpermitname
import pyramid.httpexceptions as exc

valid_searches = {"lev", "soundex", "meta", "dmeta", "fulltext"}


@view_defaults(renderer='../templates/mytemplate.jinja2')
@view_config(route_name='search', renderer='json')
def search(request):
    """
    Multi-purpose search endpoint, taking various search types.
    :param request: The Pyramid request object
    :return: A JSON response
    """

    if 'type' in request.params:
        searchtype = request.params['type']
        if searchtype not in valid_searches:
            return exc.HTTPBadRequest(detail=f"Invalid search type '{searchtype}'.")
    else:
        searchtype = 'lev'
    if 'term' in request.params:
        xhr = True
        request.response.headers.update({
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST,GET,DELETE,PUT,OPTIONS',
            'Access-Control-Allow-Headers': 'Origin, Content-Type, Accept, Authorization',
            'Access-Control-Allow-Credentials': 'true',
            'Access-Control-Max-Age': '1728000',
        })
        name = request.params['term'].upper()
        searchtype = "lev"
    else:
        xhr = False
        if 'name' not in request.params:
            return exc.HTTPBadRequest(detail="No name in search request.")
        name = request.params['name']
    if 'limit' not in request.params:
        limit = 20
    else:
        if int(request.params['limit']) > 200:
            return exc.HTTPBadRequest(detail="Limit too high (Over 200)")
        limit = int(request.params['limit'])
    if len('name') < 3:
        return exc.HTTPBadRequest(detail="Name too short.")

    permsystems = request.dbsession.query(Permits)
    perm_systems = []
    candidates = []
    result = None
    for system in permsystems:
        perm_systems.append(system.id64)
    # Ensure we're not wasting cycles on someone searching an exact system name on this endpoint.
    # func.similarity(System.name, name).label('similarity'))
    match = request.dbsession.query(System, func.similarity(System.name, name).label('similarity')). \
        filter(System.name.ilike(name)).order_by(func.similarity(System.name, name).desc()).limit(1)
    for candidate in match:
        candidates.append({'name': candidate[0].name, 'similarity': 1,
                           'id64': candidate[0].id64,
                           'permit_required': True if candidate[0].id64 in perm_systems else False,
                           'permit_name': checkpermitname(candidate[0].id64, permsystems, perm_systems)
                           })
    if match.count() > 0:
        return {'meta': {'name': candidate[0].name, 'type': 'Perfect match'}, 'data': candidates}
    if len(name) < 3:
        return exc.HTTPBadRequest(detail="Search term too short (Minimum 3 characters)")

    if searchtype == 'lev':
        result = request.dbsession.query(System, func.similarity(System.name, name).label('similarity')). \
            filter(System.name.ilike(f"{name}%")).order_by(func.similarity(System.name, name).desc()).limit(limit)
        for row in result:
            candidates.append({'name': row[0].name, 'similarity': row[1], 'id64': row[0].id64,
                               'permit_required': True if row[0].id64 in perm_systems else False,
                               'permit_name': checkpermitname(row[0].id64, permsystems, perm_systems)
                               })
        return {'meta': {'name': name, 'type': searchtype, 'limit': limit}, 'data': candidates}

    if searchtype == 'soundex':
        sql = text(f"SELECT *, similarity(name, '{name}') AS similarity FROM systems "
                   f"WHERE soundex(name) = soundex('{name}') ORDER BY "
                   f"similarity(name, '{name}') DESC LIMIT {limit}")
    if searchtype == 'meta':
        if 'sensitivity' not in request.params:
            sensitivity = 5
        else:
            sensitivity = request.params['sensitivity']
        sql = text(f"SELECT *, similarity(name,  {name}) AS similarity FROM systems "
                   f"WHERE metaphone(name, '{str(sensitivity)}') = metaphone('{name}', "
                   f"'{str(sensitivity)}') ORDER BY similarity DESC LIMIT {str(limit)}")
    if searchtype == 'dmeta':
        sql = text(f"SELECT *, similarity(name, '{name}') AS similarity FROM systems "
                   f"WHERE dmetaphone(name) = dmetaphone('{name}') ORDER BY similarity DESC LIMIT {str(limit)}")
    if searchtype == "fulltext":
        sql = text(f"SELECT name, id64, similarity(name, '{name}') AS similarity FROM systems "
                   f"WHERE name LIKE '{name}%' ORDER BY similarity DESC LIMIT {str(limit)}")
    if not result:
        # We haven't gotten a ORM result yet, execute manual SQL.
        result = request.dbsession.execute(sql)
    for row in result:
        candidates.append({'name': row['name'], 'similarity': row['similarity'], 'id64': row['id64'],
                           'permit_required': True if row.id64 in perm_systems else False,
                           'permit_name': checkpermitname(row.id64, permsystems, perm_systems)
                           })
    return {'meta': {'name': name, 'type': searchtype, 'limit': limit}, 'data': candidates}
