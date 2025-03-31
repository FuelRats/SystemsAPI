import json

from pyramid.view import (
    view_config,
    view_defaults
)
from pyramid.response import Response
from sqlalchemy import text

from ..models import System
import pyramid.httpexceptions as exc


@view_defaults(renderer='../templates/mytemplate.jinja2')
@view_config(route_name='typeahead', renderer='json')
def search(request):
    """
    Type-ahead provider for forms and similar.
    :param request: The Pyramid request object
    :return: A JSON response
    """
    request.response.headers.update({
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST,GET,DELETE,PUT,OPTIONS',
        'Access-Control-Allow-Headers': 'Origin, Content-Type, Accept, Authorization',
        'Access-Control-Allow-Credentials': 'true',
        'Access-Control-Max-Age': '1728000',
    })
    if 'term' in request.params:
        name = request.params['term'].lower()
    else:
        return exc.HTTPBadRequest(detail="No name in search request.")
    if len(name) < 3:
        return exc.HTTPBadRequest(detail="Typeahead term too short (Minimum 3 characters)")

    query = text("""
                 SET LOCAL work_mem = '100MB';
                 SELECT name
                 FROM systems
                 WHERE lower(name) LIKE lower(:prefix)
                 ORDER BY name <-> :term DESC
                     LIMIT 10
                 """)

    result = request.dbsession.execute(query, {
        "prefix": f"{name}%",
        "term": name})

    candidates = [row[0] for row in result]
    return candidates