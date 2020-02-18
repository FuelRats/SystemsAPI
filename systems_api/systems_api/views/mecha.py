from pyramid.view import (
    view_config,
    view_defaults
)
from sqlalchemy import text, func
from ..models import System, Permits
import pyramid.httpexceptions as exc


@view_defaults(renderer='../templates/mytemplate.jinja2')
@view_config(route_name='mecha', renderer='json')
def mecha(request):
    """
    Mecha dedicated endpoint that tries to be smrt about searching.
    :param request: The Pyramid request object
    :return: A JSON response
    """
    if 'name' not in request.params:
        return exc.HTTPBadRequest(detail="Missing 'name' parameter.")
    candidates = []
    permsystems = request.dbsession.query(Permits)
    perm_systems = []
    for system in permsystems:
        perm_systems.append(system.id64)
    name = request.params['name']
    if len(name) < 3:
        return exc.HTTPBadRequest(detail="Search term too short (Minimum 3 characters)")
    # Check for immediate match, case insensitive.
    query = request.dbsession.query(System).filter(System.name.ilike(name))
    for candidate in query:
        candidates.append({'name': candidate.name, 'similarity': 1,
                           'id64': candidate.id64,
                           'permit_required': True if candidate.id64 in perm_systems else False,
                           'permit_name': permsystems.get(candidate.id64).permit_name or None
                           })
    if len(candidates) > 0:
        return {'meta': {'name': name, 'type': 'Perfect match'}, 'data': candidates}
    # Try soundex and dmetaphone matches on the name, look for low levenshtein distances.
    qtext = text("select *, levenshtein(name, :name) as lev from systems where dmetaphone(name) "
                 "= dmetaphone(:name) OR soundex(name) = soundex(:name) order by lev")
    query = request.dbsession.query(System).from_statement(qtext).params(name=name)
    for candidate in query:
        candidates.append({'name': candidate.name, 'distance': candidate.lev,
                           'id64': candidate.id64,
                           'permit_required': True if candidate.id64 in perm_systems else False,
                           'permit_name': permsystems.get(candidate.id64).permit_name or None
                           })
    if len(candidates) > 0:
        return {'meta': {'name': name, 'type': 'dmeta+soundex'}, 'data': candidates}
    # Try an ILIKE with wildcard on end. Slower.
    query = request.dbsession.query(System, func.similarity(System.name, name).label('similarity')).\
        filter(System.name.ilike(name+"%")).limit(10).from_self().order_by(func.similarity(System.name, name).desc())
    for candidate in query:
        candidates.append({'name': candidate[0].name, 'similarity': candidate[1],
                           'id64': candidate[0].id64,
                           'permit_required': True if candidate[0].id64 in perm_systems else False,
                           'permit_name': permsystems.get(candidate[0].id64).permit_name or None if candidate[0].id64 in perm_systems else False
                           })
    if len(candidates) > 0:
        return {'meta': {'name': name, 'type': 'wildcard'}, 'data': candidates}
    # Try a GIN trigram similarity search on the entire database. Slow as hell.
    pmatch = request.dbsession.query(System, func.similarity(System.name, name).label('similarity')). \
        filter(System.name % name).limit(10).from_self().order_by(func.similarity(System.name, name).desc())
    if pmatch.count() > 0:
        for candidate in pmatch:
            # candidates.append({'name': candidate[0].name, 'similarity': "1.0"}
            candidates.append({'name': candidate[0].name, 'similarity': candidate[1],
                               'id64': candidate[0].id64,
                               'permit_required': True if candidate[0].id64 in perm_systems else False,
                               'permit_name': permsystems.get(candidate[0].id64).permit_name or None if candidate[
                                                                                                            0].id64 in perm_systems else False
                               })
    if len(candidates) < 1:
        # We ain't got shit. Give up.
        return {'meta': {'name': name, 'error': 'No hits.'}}
    return {'meta': {'name': name}, 'data': candidates}
