from pyramid.view import (
    view_config,
    view_defaults
)

import pyramid.httpexceptions as exc

from ..utils import pgnames


@view_defaults(renderer='../templates/mytemplate.jinja2')
@view_config(route_name='procname', renderer='json')
def procnames(request):
    if 'name' not in request.params:
        return exc.HTTPBadRequest(details='Missing name parameter')
    name = request.params['name']
    if pgnames.is_pg_system_name(name):
        return {'is_pg_system': True}
    else:
        return {'is_pg_system': False}
