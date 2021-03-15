from pyramid.view import (
    view_config,
    view_defaults
)

import pyramid.httpexceptions as exc

from ..utils import pgnames, system
import json


@view_defaults(renderer='../templates/mytemplate.jinja2')
@view_config(route_name='procname', renderer='json')
def procnames(request):
    if 'name' not in request.params:
        return exc.HTTPBadRequest(details='Missing name parameter')
    if pgnames.is_pg_system_name(request.params['name']):
        return {'is_pg_system': pgnames.is_pg_system_name(request.params['name'], True),
                'is_pg_sector': pgnames.is_valid_sector_name(request.params['name']),
                'sectordata': pgnames.get_system(pgnames.get_canonical_name(request.params['name']))}
    else:
        return {'is_pg_system': pgnames.is_pg_system_name(request.params['name'], True),
                'is_pg_sector': pgnames.is_valid_sector_name(request.params['name'])}


@view_defaults(renderer='../templates/mytemplate.jinja2')
@view_config(route_name='proccoords', renderer='json')
def proccoords(request):
    if 'name' not in request.params:
        return exc.HTTPBadRequest(details='Missing name parameter')
    name = pgnames.get_canonical_name(request.params['name'])
    return pgnames.get_system(name)


@view_defaults(renderer='../templates/mytemplate.jinja2')
@view_config(route_name='get_ha_regions', renderer='json')
def get_ha_regions(request):
    regions = pgnames.get_ha_regions()
    ret = []
    for region in regions:
        ret.append(region)
    return ret
