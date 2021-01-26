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
    return {'is_pg_system': pgnames.is_pg_system_name(request.params['name'], True),
            'is_pg_sector': pgnames.is_valid_sector_name(request.params['name'])}
