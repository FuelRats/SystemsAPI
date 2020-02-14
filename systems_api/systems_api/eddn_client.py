import zlib
import transaction
import zmq
import simplejson
import sys
import time
import os
import semver

from xmlrpc.client import ServerProxy, Error, ProtocolError

from pyramid.paster import (
    get_appsettings,
    setup_logging,
    )

from pyramid.scripts.common import parse_vars
from sqlalchemy import func
from sqlalchemy.exc import DataError

from .models import (
    get_engine,
    get_session_factory,
    get_tm_session,
    )


from .models import Star, System

__relayEDDN = 'tcp://eddn.edcd.io:9500'
__timeoutEDDN = 600000
__scoopable = ['K', 'G', 'B', 'F', 'O', 'A', 'M']

__allowedSchema = [
    "https://eddn.edcd.io/schemas/journal/1"
]

__blockedSoftware = [
    "ed-ibe (api)".casefold(),
    "ed central production server".casefold(),
    "eliteocr".casefold(),
    "regulatednoise__dj".casefold(),
    "ocellus - elite: dangerous assistant".casefold(),
    "eva".casefold()
]


def validsoftware(name, version):
    if not name:
        return False
    if not version:
        return False
    ver = semver.parse(version)
    if name.casefold() == "e:d market connector".casefold():
        if semver.compare(version, "2.4.9.0") < 0:
            print("Ignored old EDMC message.")
            return False
    if name.casefold() == "EDDiscovery".casefold():
        if semver.compare(version, "9.1.1.0") < 0:
            print("Ignored old EDDiscovery message.")
            return False
    if name.casefold() == "EDDI".casefold():
        if semver.compare(version, "2.4.5") < 0:
            print("Ignored old EDDI message.")
            return False
    if name.casefold() == "Moonlight".casefold():
        if semver.compare(version, "1.3.4") < 0:
            print("Ignored old Moonlight message.")
            return False
    if name.casefold() in __blockedSoftware:
        print(f"Ignored blocked software {name}")
        return False
    return True


def usage(argv):
    cmd = os.path.basename(argv[0])
    print('usage: %s <config_uri> [var=value]\n'
          '(example: "%s development.ini")' % (cmd, cmd))
    sys.exit(1)


def main(argv=sys.argv):
    if len(argv) < 2:
        usage(argv)
    config_uri = argv[1]
    options = parse_vars(argv[2:])
    setup_logging(config_uri)
    settings = get_appsettings(config_uri, name='mainapp', options=options)
    engine = get_engine(settings)
    session_factory = get_session_factory(engine)
    session = get_tm_session(session_factory, transaction.manager)
    serverurl = settings['xml_proxy'] if 'xml_proxy' in settings else 'https://irc.eu.fuelrats.com:6080/xmlrpc'
    proxy = ServerProxy(serverurl)

    context = zmq.Context()
    subscriber = context.socket(zmq.SUB)

    subscriber.setsockopt(zmq.SUBSCRIBE, b"")
    subscriber.setsockopt(zmq.RCVTIMEO, __timeoutEDDN)
    starttime = time.time()
    lasthourly = time.time()
    messages = 0
    syscount = 0
    starcount = 0
    totmsg = 0
    hmessages= 0
    proxy.command("botserv", "Absolver", "say #rattech [SAPI]: EDDN client has started.")
    while True:
        try:
            subscriber.connect(__relayEDDN)

            while True:
                __message = subscriber.recv()

                if not __message:
                    subscriber.disconnect(__relayEDDN)
                    break

                __message = zlib.decompress(__message)
                __json = simplejson.loads(__message)
                totmsg = totmsg + 1
                if validsoftware(__json['header']['softwareName'], __json['header']['softwareVersion'])\
                        and __json['$schemaRef'] in __allowedSchema:

                    if time.time() > (starttime + 3600 * 24):
                        try:
                            startot = session.query(func.count(Star.id64)).scalar()
                            systot = session.query(func.count(System.id64)).scalar()
                            proxy.command("botserv", "Absolver", f"say #ratchat [\x0315SAPI\x03] Daily report: "
                                                                 f"{'{:,}'.format(messages)} messages processed"
                                                                 f", {'{:,}'.format(syscount)} new systems,"
                                                                 f"  {'{:,}'.format(starcount)} new stars."
                                                                 f" DB contains {'{:,}'.format(startot)} stars "
                                                                 f"and {'{:,}'.format(systot)} systems.")
                            messages = 0
                            syscount = 0
                            starcount = 0
                            starttime = time.time()
                        except TimeoutError:
                            print("XMLRPC call failed due to timeout, retrying in 60 seconds.")
                            starttime = starttime + 60
                        except ProtocolError as e:
                            print(f"XMLRPC call failed, skipping this update. {e.errmsg}")
                            starttime = time.time()
                    if time.time() > (lasthourly + 3600):
                        try:
                            proxy.command(f"botserv", "Absolver", f"say #announcerdev [\x0315SAPI\x03] Hourly report:"
                                          f" {hmessages}, {totmsg-hmessages} ignored.")
                            lasthourly = time.time()
                            totmsg = 0
                            hmessages = 0

                        except TimeoutError:
                            print("XMLRPC call failed due to timeout, retrying in 60 seconds.")
                            lasthourly = lasthourly + 60
                        except ProtocolError as e:
                            print(f"XMLRPC call failed, skipping this update. {e.errmsg}")
                            lasthourly = time.time()

                    data = __json['message']
                    messages = messages + 1
                    if 'event' in data:
                        if data['event'] == 'FSDJump':
                            id64 = data['SystemAddress']
                            res = session.query(System.id64).filter(System.id64 == id64).scalar() or False
                            if not res:
                                syscount = syscount + 1
                                newsys = System(id64=data['SystemAddress'], name=data['StarSystem'],
                                                coords=data['StarPos'], date=data['timestamp'])
                                try:
                                    session.add(newsys)
                                    transaction.commit()
                                except DataError:
                                    print("Failed to add a system! Invalid data passed")
                                    transaction.abort()
                        if data['event'] == 'Scan':
                            bodyid = data['SystemAddress'] + (data['BodyID'] << 55)
                            if 'AbsoluteMagnitude' in data:
                                res = session.query(Star.id64).filter(Star.id64 == bodyid).scalar() or False
                                if not res:
                                    starcount = starcount + 1
                                    newstar = Star(id64=bodyid, bodyId=data['BodyID'], name=data['BodyName'],
                                                   age=data['Age_MY'], axialTilt=data['AxialTilt'],
                                                   orbitalEccentricity=data['Eccentricity']
                                                   if 'Eccentricity' in data else None,
                                                   orbitalInclination=data['OrbitalInclination']
                                                   if 'OrbitalInclination' in data else None,
                                                   orbitalPeriod=data['OrbitalPeriod']
                                                   if 'OrbitalPeriod' in data else None,
                                                   parents=data['Parents']
                                                   if 'Parents' in data else None,
                                                   argOfPeriapsis=data['Periapsis']
                                                   if 'Periapsis' in data else None,
                                                   belts=data['Rings'] if 'Rings' in data else None,
                                                   semiMajorAxis=data['SemiMajorAxis']
                                                   if 'SemiMajorAxis' in data else None,
                                                   systemName=data['StarSystem'],
                                                   distanceToArrival=data['DistanceFromArrivalLS'],
                                                   luminosity=data['Luminosity'], solarRadius=data['Radius'],
                                                   rotationalPeriod=data['RotationPeriod'], type=data['StarType'],
                                                   solarMasses=data['StellarMass'],
                                                   subType=data['Subclass'] if 'Subclass' in data else None,
                                                   surfaceTemperature=data['SurfaceTemperature'],
                                                   isScoopable=True if data['StarType'] in __scoopable else False,
                                                   isMainStar=True if data['BodyID'] == 0 else False,
                                                   updateTime=data['timestamp'])
                                    try:
                                        session.add(newstar)
                                        print("Added new star.")
                                        transaction.commit()
                                    except DataError:
                                        print("Failed to add star - Data Error!")
                                        transaction.abort()
                sys.stdout.flush()

        except zmq.ZMQError as e:
            print('ZMQSocketException: ' + str(e))
            proxy.command("botserv", "Absolver", f"say #rattech [\x0315SAPI\x03] EDDN error: "
                                                 f"Exiting due to exception: {str(e)}")

            sys.stdout.flush()
            subscriber.disconnect(__relayEDDN)
            time.sleep(5)


if __name__ == '__main__':
    main()
