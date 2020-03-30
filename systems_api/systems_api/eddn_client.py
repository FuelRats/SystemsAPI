import zlib
import transaction
import zmq
import simplejson
import sys
import time
import os
import semver
import re

from xmlrpc.client import ServerProxy, ProtocolError

from pyramid.paster import (
    get_appsettings,
    setup_logging,
    )

from pyramid.scripts.common import parse_vars
from sqlalchemy import func
from sqlalchemy.exc import DataError

from systems_api.models import (
    get_engine,
    get_session_factory,
    get_tm_session,
    )


from systems_api.models.star import Star
from systems_api.models.system import System
from systems_api.models.stats import Stats
from systems_api.models.body import Body

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

BASEVERSION = re.compile(
    r"""[vV]?
        (?P<major>0|[1-9]\d*)
        (\.
        (?P<minor>0|[1-9]\d*)
        (\.
            (?P<patch>0|[1-9]\d*)
        )?
        )?
    """,
    re.VERBOSE,
)


def coerce(version):
    """
    Convert an incomplete version string into a semver-compatible VersionInfo
    object

    * Tries to detect a "basic" version string (``major.minor.patch``).
    * If not enough components can be found, missing components are
        set to zero to obtain a valid semver version.

    :param str version: the version string to convert
    :return: a tuple with a :class:`VersionInfo` instance (or ``None``
        if it's not a version) and the rest of the string which doesn't
        belong to a basic version.
    :rtype: tuple(:class:`VersionInfo` | None, str)
    """
    match = BASEVERSION.search(version)
    if not match:
        return version

    ver = {
        key: 0 if value is None else value
        for key, value in match.groupdict().items()
    }
    ver = str(semver.VersionInfo(**ver))
    return ver


def validsoftware(name, version):
    if not name:
        return False
    if not version:
        return False
    ver = coerce(version)

    if name.casefold() == "e:d market connector".casefold():
        if semver.compare(ver, "2.4.9") < 0:
            print("Ignored old EDMC message.")
            return False
    if name.casefold() == "EDDiscovery".casefold():
        if semver.compare(ver, "9.1.1") < 0:
            print("Ignored old EDDiscovery message.")
            return False
    if name.casefold() == "EDDI".casefold():
        if semver.compare(ver, "2.4.5") < 0:
            print("Ignored old EDDI message.")
            return False
    if name.casefold() == "Moonlight".casefold():
        if semver.compare(ver, "1.3.4") < 0:
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
    proxy = None
    serverurl = None
    config_uri = argv[1]
    options = parse_vars(argv[2:])
    setup_logging(config_uri)
    settings = get_appsettings(config_uri, options=options)
    engine = get_engine(settings)
    session_factory = get_session_factory(engine)
    session = get_tm_session(session_factory, transaction.manager)
    if 'xml_proxy' in settings:
        serverurl = settings['xml_proxy']
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
    if proxy:
        try:
            proxy.command("botserv", "Absolver", "say #rattech [SAPI]: EDDN client has started.")
        except ProtocolError as e:
            print(f"Failed to send start message to XMLRPC. {e.errmsg}")
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
                print(f"EDDN Client running. Messages: {messages:10} Stars: {starcount:10} Systems: {syscount:10}\r", end='')
                if validsoftware(__json['header']['softwareName'], __json['header']['softwareVersion'])\
                        and __json['$schemaRef'] in __allowedSchema:

                    if proxy:
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
                            startot = session.query(func.count(Star.id64)).scalar()
                            systot = session.query(func.count(System.id64)).scalar()
                            bodytot = session.query(func.count(Body.id64)).scalar()
                            newstats = Stats(syscount=systot, starcount=startot, bodycount=bodytot,
                                             lastupdate=time.time())
                            session.query(Stats).delete()
                            session.add(newstats)
                            try:
                                proxy.command(f"botserv", "Absolver", f"say #announcerdev [\x0315SAPI\x03] Hourly report:"
                                              f" {hmessages} messages, {totmsg-hmessages} ignored.")
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
