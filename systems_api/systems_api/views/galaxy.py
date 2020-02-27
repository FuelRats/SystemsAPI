from pyramid.view import view_config
import colander
from deform import Form, ValidationFailure, widget
from sqlalchemy import func

from ..models import System, PopulatedSystem


class Galaxy(colander.MappingSchema):
    area = (('Populated', 'Populated'), ('Galaxy', 'Galaxy'))
    system_name = colander.SchemaNode(colander.String(),
                                      description="System name (Or something close to it")
    search_area = colander.SchemaNode(colander.String(), widget=widget.SelectWidget(values=area),
                                      validator=colander.OneOf(('Populated', 'Galaxy')),
                                      description="Search only populated systems, or all systems?")


@view_config(route_name='galaxy', renderer='../templates/form.jinja2')
def my_view(request):
    schema = Galaxy()
    gform = Form(schema, buttons=('Search',))
    if 'submit' in request.POST:
        controls = request.POST.items()
        try:
            appstruct = gform.validate(controls)
            system_name = appstruct.pop('system_name', "InvalidSystem")
            search_area = appstruct.pop('search_area', "InvalidSearchArea")
            if search_area == 'Populated':
                res = request.dbsession.query(PopulatedSystem, func.similarity(PopulatedSystem.name, system_name).\
                                              label('similarity')).filter(PopulatedSystem.name % system_name).\
                                              order_by(func.similarity(PopulatedSystem.name, system_name).desc())
            else:
                res = request.dbsession.query(System, func.similarity(System.name, system_name).\
                                              label('similarity')).filter(System.name % system_name).\
                                              order_by(func.similarity(System.name, system_name).desc())
            results = []
            for candidate in res:
                results.append()
        except:
            print("OOps?!")
