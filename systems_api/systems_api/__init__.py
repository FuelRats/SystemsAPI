from pyramid.config import Configurator
import pyramid_jsonapi
from . import models

# Hard ceiling on the number of rows a single JSON:API collection GET may pull
# into memory. pyramid_jsonapi fetches the whole collection with query.all()
# and slices the requested page in Python (workflow/loop/collection_get.py), so
# without a SQL LIMIT an unfiltered GET on a huge table (systems/bodies/stars)
# materialises the entire table and exhausts memory. The alter_query handler
# below bounds every collection query to the requested page.
MAX_COLLECTION_ROWS = 1000


def cap_collection_query(query, view, stage=None, view_method=None, **kwargs):
    """Bound a collection query to the requested page so query.all() can never
    materialise an entire table."""
    paging = view.query_info.paging_info
    cap = min(paging.limit + paging.offset, MAX_COLLECTION_ROWS)
    return query.limit(cap)


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    with Configurator(settings=settings) as config:
        config.include('.models')
        config.include('pyramid_jinja2')
        config.include('.routes')
        config.registry.settings['pyramid_jsonapi.paging_max_limit'] = 100
        config.scan()
        pj = pyramid_jsonapi.PyramidJSONAPI(config, models)
        pj.create_jsonapi_using_magic_and_pixie_dust()
        for view_class in pj.view_classes.values():
            view_class.add_stage_handler(
                ['collection_get'], ['alter_query'], cap_collection_query,
            )
    return config.make_wsgi_app()
