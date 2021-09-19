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
    edsm_system = None
    data = {'deleted_stars': 0, 'deleted_bodies': 0, 'deleted_stations': 0, 'is_new_system': False,
            'added_stars': 0, 'added_bodies': 0, 'added_stations': 0,
            'fc_skipped': 0, 'is_populated': False}
    if 'systemName' not in request.params and 'systemId' not in request.params:
        return exc.HTTPBadRequest('Missing systemName or systemId parameter')
    if 'systemId' in request.params:
        print("Fetch EDSM system info")
        edsm_system = edsm.fetch_edsm_system_by_id(request.params['systemId'])
        if not edsm_system:
            return exc.HTTPBadRequest('No EDSM with that systemID.')
        systemName = edsm_system['systemName']
    else:
        systemName = request.params['systemName']
    if systemName:
        print("Look up own system data...")
        sys = request.dbsession.query(System).filter(System.name == systemName).first()
        if not sys:
            print("No system, lookup in populated...")
            sys = request.dbsession.query(PopulatedSystem).filter(PopulatedSystem.name == systemName).first()
        if sys:
            print(f"Got system with id {sys.id64}. Fetching for canonical name {sys.name}")
            edsm_system = edsm.fetch_edsm_system_by_name(sys.name)
            print(f"Got json: {edsm_system}")
            if sys.id64 != edsm_system['id64'] and 'force' not in request.params:
                print("ERROR! The systemId64 in EDSM does not match the SAPI systemID64. This is probably bad.")
                return {'Error': f'SystemID64 returned from EDSM does not match SAPI ID64. SAPI ID64 {sys.id64} is for '
                                 f'{sys.name}, EDSM claims it is {edsm_system["name"]}. Verify system is correct and '
                                 f'pass force=True as a parameter to override.'}
        else:
            print(f"Unknown system for us, fetch by input name from EDSM.")
            if not edsm_system:
                edsm_system = edsm.fetch_edsm_system_by_name(request.params['systemName'])
            if not edsm_system:
                return exc.HTTPBadRequest('System name does not exist in SAPI or EDSM.')
            print(f"Json: {edsm_system}")
            print(f"Creating new system.")
            data['is_new_system'] = True
            if edsm_system['information']['population'] > 0:
                print("System is populated.")
                data['is_populated'] = True
                sys = PopulatedSystem(id64=edsm_system['id64'], name=edsm_system['name'], coords=edsm_system['coords'],
                                      controllingFaction=edsm_system['information'], date=datetime.datetime.utcnow())
            else:
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
            data['deleted_stars'] += 1
        for row in sbodies:
            print(f"Body {row.name} with ID {row.id64} up for deletion.")
            data['deleted_bodies'] += 1
        print(f"Ready to replace {data['deleted_stars']} stars, {data['deleted_bodies']} bodies and "
              f"{data['deleted_stations']} stations.")
        sys.id64 = edsm_system['id64']
        sys.name = edsm_system['name']
        sys.coords = edsm_system['coords']
        sys.date = datetime.datetime.utcnow()
        request.dbsession.flush()
        sstars.delete()
        sbodies.delete()
        sstations.delete()
        transaction.commit()

        print("Adding stations...")
        for station in edsm_stations['stations']:
            if station['type'] == 'Fleet Carrier':
                print("Skipping FC.")
                data['fc_skipped'] += 1
                continue
            print(f"Station {station['name']} with ID {station['id']}.")
            newstation = Station(id64=station['marketId'], marketId=station['marketId'], type=station['type'],
                                 name=station['name'], distanceToArrival=station['distanceToArrival'],
                                 allegiance=station['allegiance'], government=station['government'],
                                 economy=station['economy'], haveMarket=station['haveMarket'],
                                 haveShipyard=station['haveShipyard'], haveOutfitting=station['haveOutfitting'],
                                 otherServices=station['otherServices'], updateTime=station['updateTime']['information'],
                                 systemId64=edsm_system['id64'], systemName=edsm_system['name'])
            request.dbsession.add(newstation)
            data['added_stations'] += 1
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
                data['added_stars'] += 1
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
                data['added_bodies'] += 1
                request.dbsession.add(newbody)
        transaction.commit()
        print("Operations completed.")
        return {'status': 'Success', 'data': data}
