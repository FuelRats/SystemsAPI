from pyramid.view import (
    view_config,
    view_defaults
)
from sqlalchemy import text, func, column
from ..models import System, Permits
import pyramid.httpexceptions as exc
from ..utils.util import checkpermitname, resultstocandidates
from ..utils.pgnames import is_pg_system_name
from urllib.parse import unquote
import re

pg_system_regex_str = r"^(?P<l1>[A-Za-z])(?P<l2>[A-Za-z])-(?P<l3>[A-Za-z]) (?P<mcode>[A-Za-z])(?:(?P<n1>\d+)-)?(?P<n2>\d+)"
pg_system_search_regex = re.compile(pg_system_regex_str)
pg_system_regex = re.compile(r"^" + pg_system_regex_str + r"$")


@view_defaults(renderer='../templates/mytemplate.jinja2')
@view_config(route_name='mecha', renderer='json')
def mecha(request):
    """
    Optimized Mecha endpoint focusing on fastest returns for precise matches.
    """
    if 'name' not in request.params:
        return exc.HTTPBadRequest(detail="Missing 'name' parameter.")

    name = unquote(request.params['name']).strip()
    if len(name) < 3:
        return exc.HTTPBadRequest(detail="Search term too short (Minimum 3 characters)")

    lname = name.lower()
    permsystems = request.dbsession.query(Permits).all()
    perm_systems = {system.id64 for system in permsystems}

    # Case-sensitive exact match
    exact_match = request.dbsession.query(System).filter(System.name == name).first()
    if exact_match:
        return {'meta': {'name': name, 'type': 'Perfect match'}, 'data': [{
            'name': exact_match.name,
            'similarity': 1,
            'id64': exact_match.id64,
            'coords': exact_match.coords,
            'permit_required': exact_match.id64 in perm_systems,
            'permit_name': checkpermitname(exact_match.id64, permsystems, perm_systems)
        }]}

    # Case-insensitive exact match
    ci_match = request.dbsession.query(System).filter(func.lower(System.name) == lname).first()
    if ci_match:
        return {'meta': {'name': name, 'type': 'Case-insensitive match'}, 'data': [{
            'name': ci_match.name,
            'similarity': 1,
            'id64': ci_match.id64,
            'coords': ci_match.coords,
            'permit_required': ci_match.id64 in perm_systems,
            'permit_name': checkpermitname(ci_match.id64, permsystems, perm_systems)
        }]}

    if 'fast' in request.params:
        return {'meta': {'error': 'System not found. Query again without fast flag for in-depth search.',
                         'type': 'notfound'}}

    # PG system handling
    if pg_system_regex.match(name):
        return {'meta': {'error': 'Incomplete PG system name.', 'type': 'incomplete_name'}}

    if is_pg_system_name(name):
        qtext = text("""
            SET LOCAL work_mem = '100MB';
            SELECT *, similarity(name, :name) as lev
            FROM systems
            WHERE lower(name) LIKE :prefix
            ORDER BY name <-> :name
            LIMIT 10
        """)
        results = request.dbsession.query(System, column('lev')).from_statement(qtext).params(
            name=lname, prefix=f"{lname}%"
        ).all()
        if results:
            return {'meta': {'name': name, 'type': 'pg_trgm'}, 'data': [
                {'name': c[0].name, 'similarity': c[1],
                 'id64': c[0].id64, 'coords': c[0].coords,
                 'permit_required': c[0].id64 in perm_systems,
                 'permit_name': checkpermitname(c[0].id64, permsystems, perm_systems)}
                for c in results
            ]}

    # Soundex and DMetaphone matches
    qtext = text("""
        SET LOCAL work_mem = '100MB';
        WITH matches AS (
            SELECT id64, name, levenshtein(lower(name), :lname) as lev
            FROM systems
            WHERE soundex(name) = soundex(:name) OR dmetaphone(name) = dmetaphone(:name)
            ORDER BY lev ASC
            LIMIT 10
        ) SELECT * FROM matches WHERE lev < 3;
    """)
    results = request.dbsession.query(System, column('lev')).from_statement(qtext).params(name=name, lname=lname).all()
    if results:
        return {'meta': {'name': name, 'type': 'phonetic'}, 'data': [
            {'name': c[0].name, 'distance': c[1],
             'id64': c[0].id64, 'coords': c[0].coords,
             'permit_required': c[0].id64 in perm_systems,
             'permit_name': checkpermitname(c[0].id64, permsystems, perm_systems)}
            for c in results
        ]}

    # Wildcard ILIKE search
    wildcard_results = request.dbsession.query(System, func.similarity(System.name, name).label('sim')).\
        filter(func.lower(System.name).like(f"{lname}%")).order_by(func.similarity(System.name, name).desc()).limit(10).all()

    if wildcard_results:
        return {'meta': {'name': name, 'type': 'wildcard'}, 'data': [
            {'name': c[0].name, 'similarity': c[1],
             'id64': c[0].id64, 'coords': c[0].coords,
             'permit_required': c[0].id64 in perm_systems,
             'permit_name': checkpermitname(c[0].id64, permsystems, perm_systems)}
            for c in wildcard_results
        ]}

    # Final trigram search as fallback
    qtext = text("""
        SELECT *, similarity(name, :name) as lev
        FROM systems
        WHERE name % :name
        ORDER BY lev DESC
        LIMIT 10
    """)
    results = request.dbsession.query(System, column('lev')).from_statement(qtext).params(name=name).all()

    if results:
        return {'meta': {'name': name, 'type': 'gin_trgm'}, 'data': [
            {'name': c[0].name, 'similarity': c[1],
             'id64': c[0].id64, 'coords': c[0].coords,
             'permit_required': c[0].id64 in perm_systems,
             'permit_name': checkpermitname(c[0].id64, permsystems, perm_systems)}
            for c in results
        ]}

    return {'meta': {'error': 'System not found.', 'type': 'notfound'}}
