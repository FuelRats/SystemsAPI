from pyramid.view import (
    view_config,
    view_defaults
)
from sqlalchemy import text, func
from ..models import System, Permits
import pyramid.httpexceptions as exc
from ..utils.util import checkpermitname, resultstocandidates
from ..utils.pgnames import is_pg_system_name


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
    name = request.params['name']
    if len(name) < 3:
        return exc.HTTPBadRequest(detail="Search term too short (Minimum 3 characters)")
    candidates = []
    permsystems = request.dbsession.query(Permits)
    perm_systems = []
    for system in permsystems:
        perm_systems.append(system.id64)

    # Check for immediate match, case insensitive.
    query = request.dbsession.query(System).filter(System.name.ilike(name))
    for candidate in query:
        candidates.append({'name': candidate.name, 'similarity': 1,
                           'id64': candidate.id64,
                           'permit_required': True if candidate.id64 in perm_systems else False,
                           'permit_name': checkpermitname(candidate.id64, permsystems, perm_systems)
                           })
    if len(candidates) > 0:
        return {'meta': {'name': name, 'type': 'Perfect match'}, 'data': candidates}
    if 'fast' in request.params:
        return {'meta': {'error': 'System not found. Query again without fast flag for in-depth search.',
                         'type': 'notfound'}}
    if is_pg_system_name(name):
        # If the system is a PGName, don't try soundex and dmeta first, as they are most likely to fail.
        qtext = text("select *, similarity(lower(name), lower(:name)) as lev from systems where name % :name"
                     " ORDER BY lev DESC LIMIT 10")
        pmatch = request.dbsession.query(System, "lev").from_statement(qtext).params(name=name).all()
        for candidate in pmatch:
            # candidates.append({'name': candidate[0].name, 'similarity': "1.0"}
            candidates.append({'name': candidate[0].name, 'similarity': candidate[1],
                               'id64': candidate[0].id64,
                               'permit_required': True if candidate[0].id64 in perm_systems else False,
                               'permit_name': checkpermitname(candidate[0].id64, permsystems, perm_systems)
                               })
            if len(candidates) > 10:
                break
        if len(candidates) > 1:
            return {'meta': {'name': name, 'type': 'gin_trgm'}, 'data': candidates}
    # Try soundex and dmetaphone matches on the name, look for low levenshtein distances.
    qtext = text("select *, levenshtein(lower(name), lower(:name)) as lev from systems where dmetaphone(name) "
                 "= dmetaphone(:name) OR soundex(name) = soundex(:name) order by lev limit 10")
    query = request.dbsession.query(System, "lev").from_statement(qtext).params(name=name).all()
    for candidate in query:
        print(candidate)
        if candidate[1] < 5:
            candidates.append({'name': candidate[0].name, 'distance': candidate[1],
                               'id64': candidate[0].id64,
                               'permit_required': True if candidate[0].id64 in perm_systems else False,
                               'permit_name': checkpermitname(candidate[0].id64, permsystems, perm_systems)
                               })
    if len(candidates) > 0:
        return {'meta': {'name': name, 'type': 'dmeta+soundex'}, 'data': candidates}
    # Try an ILIKE with wildcard on end. Slower.
    query = request.dbsession.query(System, func.similarity(System.name, name).label('similarity')).\
        filter(System.name.ilike(name+"%")).limit(5000).from_self().order_by(func.similarity(System.name, name).desc())
    for candidate in query:
        candidates.append({'name': candidate[0].name, 'similarity': candidate[1],
                           'id64': candidate[0].id64,
                           'permit_required': True if candidate[0].id64 in perm_systems else False,
                           'permit_name': checkpermitname(candidate[0].id64, permsystems, perm_systems)
                           })
        if len(candidates) > 10:
            break
    if len(candidates) > 0:
        return {'meta': {'name': name, 'type': 'wildcard'}, 'data': candidates}
    # Try a GIN trigram similarity search on the entire database. Slow as hell.
    qtext = text("select *, similarity(lower(name), lower(:name)) as lev from systems where name % :name"
                 " ORDER BY lev DESC LIMIT 10")
    pmatch = request.dbsession.query(System, "lev").from_statement(qtext).params(name=name).all()
    if pmatch.count() > 0:
        for candidate in pmatch:
            # candidates.append({'name': candidate[0].name, 'similarity': "1.0"}
            candidates.append({'name': candidate[0].name, 'similarity': candidate[1],
                               'id64': candidate[0].id64,
                               'permit_required': True if candidate[0].id64 in perm_systems else False,
                               'permit_name': checkpermitname(candidate[0].id64, permsystems, perm_systems)
                               })
            if len(candidates) > 10:
                break
    if len(candidates) < 1:
        # We ain't got shit. Give up.
        return {'meta': {'name': name, 'error': 'No hits.'}}
    return {'meta': {'name': name, 'type': 'gin_trgm'}, 'data': candidates}
