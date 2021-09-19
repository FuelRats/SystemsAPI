import datetime

from pyramid.view import (
    view_config,
    view_defaults
)
from systems_api.models import System, Permits, Carrier, Star, PopulatedSystem, Station, Body
import pyramid.httpexceptions as exc
from systems_api.utils import edsm
import transaction


@view_defaults(renderer='../templates/mytemplate.jinja2')
@view_config(route_name='fetch_system', renderer='json')
def fetch_system(request):
    """
    Fetches new system information from EDSM, discarding any data for that system in DB.
    For correcting garbage data gotten from EDDN or bad imports.
    :param request:
    :return:
    """
    if 'systemName' not in request.params and 'systemId' not in request.params:
        return exc.HTTPBadRequest('Missing systemName or systemId parameter')
    if 'systemName' in request.params:
        print("Look up own system data...")
        sys = request.dbsession.query(System).filter(System.name == request.params['systemName']).first()
        scount = 0
        bcount = 0
        stcount = 0

        if sys:
            print(f"Got system with id {sys.id64}. Fetching for canonical name {sys.name}")
            edsm_system = edsm.fetch_edsm_system_by_name(sys.name)
            print(f"Got json: {edsm_system}")
            if sys.id64 != edsm_system['id64']:
                print("ERROR! The systemId64 in EDSM does not match the SAPI systemID64. This is probably bad.")
                return {'Error': f'SystemID64 returned from EDSM does not match SAPI ID64. SAPI ID64 {sys.id64} is for '
                                 f'{sys.name}, EDSM claims it is {edsm_system["name"]}'}
        else:
            print(f"Unknown system for us, fetch by input name.")
            edsm_system = edsm.fetch_edsm_system_by_name(request.params['systemName'])
            print(f"Creating new system.")
            sys = System(id64=edsm_system['id64'], name=edsm_system['name'], coords=edsm_system['coords'],
                         date=datetime.datetime.utcnow())
            request.dbsession.add(sys)
            transaction.commit()
            request.dbsession.flush()

        print("Fetching body data")
        edsm_bodies = edsm.fetch_edsm_bodies_by_id(edsm_system['id'])
        print(f"Got JSON: {edsm_bodies}")
        print("Fetching station data")
        edsm_stations = edsm.fetch_edsm_stations_by_id(edsm_system['id'])
        print(f"Got JSON: {edsm_stations}")
        sstars = request.dbsession.query(Star).filter(Star.systemId64 == sys.id64)
        sbodies = request.dbsession.query(Body).filter(Body.systemId64 == sys.id64)
        sstations = request.dbsession.query(Station).filter(Station.systemId64 == sys.id64)

        for row in sstars:
            print(f"Star {row.name} with ID {row.id64} up for deletion.")
            scount += 1
        for row in sbodies:
            print(f"Body {row.name} with ID {row.id64} up for deletion.")
            bcount += 1
        print(f"Ready to replace {scount} stars, {bcount} bodies and {stcount} stations.")
        sys.id64 = edsm_system['id64']
        sys.name = edsm_system['name']
        sys.coords = edsm_system['coords']
        sys.date = datetime.datetime.utcnow()
        request.dbsession.flush()
        sstars.delete()
        sbodies.delete()
        sstations.delete()
        transaction.commit()
        nstar = 0
        nbody = 0
        nstation = 0

        print("Adding stations...")
        for station in edsm_stations['stations']:
            if station['type'] == 'Fleet Carrier':
                print("Skipping FC.")
                continue
            print(f"Station {station['name']} with ID {station['id']}.")
            newstation = Station(id64=station['marketId'], marketId=station['marketId'], type=station['type'],
                                 name=station['name'], distanceToArrival=station['distanceToArrival'],
                                 allegiance=station['allegiance'], government=station['government'],
                                 economy=station['economy'], haveMarket=station['haveMarket'],
                                 haveShipyard=station['haveShipyard'], haveOutfitting=station['haveOutfitting'],
                                 otherServices=station['otherServices'],updateTime=station['updateTime']['information'])
            request.dbsession.add(newstation)
            nstation += 1
        transaction.commit()
        for body in edsm_bodies['bodies']:
            print(f"Body {body['name']} with ID64 {body['id64']} is type {body['type']}")
            if body['type'] == 'Star':
                newstar = Star(id64=body['id64'], bodyId=body['bodyId'], name=body['name'], type=body['type'],
                               subType=body['subType'], parents=body['parents'],
                               distanceToArrival=body['distanceToArrival'],
                               isMainStar=body['isMainStar'], isScoopable=body['isScoopable'], age=body['age'],
                               luminosity=body['luminosity'], absoluteMagnitude=body['absoluteMagnitude'],
                               solarMasses=body['solarMasses'], solarRadius=body['solarRadius'],
                               surfaceTemperature=body['surfaceTemperature'], orbitalPeriod=body['orbitalPeriod'],
                               semiMajorAxis=body['semiMajorAxis'], orbitalEccentricity=body['orbitalEccentricity'],
                               orbitalInclination=body['orbitalInclination'], argOfPeriapsis=body['argOfPeriapsis'],
                               rotationalPeriod=body['rotationalPeriod'],
                               rotationalPeriodTidallyLocked=body['rotationalPeriodTidallyLocked'],
                               axialTilt=body['axialTilt'], belts=body['belts'] if 'belts' in body else None,
                               updateTime=body['updateTime'],
                               systemId64=edsm_system['id64'], systemName=edsm_system['name'])
                nstar += 1
                request.dbsession.add(newstar)
            elif body['type'] == 'Planet':
                newbody = Body(id64=body['id64'], bodyId=body['bodyId'], name=body['name'], type=body['type'],
                               subType=body['subType'], parents=body['parents'],
                               distanceToArrival=body['distanceToArrival'], isLandable=body['isLandable'],
                               gravity=body['gravity'], earthMasses=body['earthMasses'], radius=body['radius'],
                               surfaceTemperature=body['surfaceTemperature'], volcanismType=body['volcanismType'],
                               atmosphereType=body['atmosphereType'],
                               atmosphereComposition=body['atmosphereComposition'], solidComposition=body['solidComposition'],
                               terraformingState=body['terraformingState'], orbitalPeriod=body['orbitalPeriod'],
                               semiMajorAxis=body['semiMajorAxis'], orbitalEccentricity=body['orbitalEccentricity'],
                               argOfPeriapsis=body['argOfPeriapsis'], rotationalPeriod=body['rotationalPeriod'],
                               rotationalPeriodTidallyLocked=body['rotationalPeriodTidallyLocked'],
                               updateTime=body['updateTime'], systemId64=edsm_system['id64'],
                               systemName=edsm_system['name'])
                nbody += 1
                request.dbsession.add(newbody)
        transaction.commit()
        print("Operations completed.")
        return {'status': 'Success', 'data': {'deleted_stars': scount, 'deleted_bodies': bcount,
                                              'deleted_stations': stcount, 'added_stars': nstar,
                                              'added_bodies': nbody, 'added_stations': nstation}}
