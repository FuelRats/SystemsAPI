import os
import sys
import transaction
from datetime import datetime

from pyramid.paster import (
    get_appsettings,
    setup_logging,
)

from pyramid.scripts.common import parse_vars
from sqlalchemy import distinct
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import NoResultFound

from systems_api.models import (
    get_engine,
    get_session_factory,
    get_tm_session,
)

from systems_api.models.system import System
from systems_api.models.populatedsystem import PopulatedSystem
from systems_api.models.station import Station


def usage(argv):
    """
    Print usage information
    :param argv: Arguments passed from system
    """
    cmd = os.path.basename(argv[0])
    print('usage: %s <config_uri> [var=value]\n'
          '(example: "%s development.ini")' % (cmd, cmd))
    sys.exit(1)


def main(argv=None):
    """
    Main function to synchronize stations' systems to PopulatedSystem table
    """
    if argv is None:
        argv = sys.argv
    if len(argv) < 2:
        usage(argv)

    config_uri = argv[1]
    options = parse_vars(argv[2:])
    setup_logging(config_uri)
    settings = get_appsettings(config_uri, options=options)

    engine = get_engine(settings)
    session_factory = get_session_factory(engine)
    session = get_tm_session(session_factory, transaction.manager)

    print(f"Starting population of PopulatedSystem table from stations data at {datetime.now()}")

    # Get distinct systemId64 values from Station table
    station_systems = session.query(distinct(Station.systemId64)).all()
    total_systems = len(station_systems)
    print(f"Found {total_systems} systems with stations")

    added = 0
    already_exists = 0
    errors = 0

    for i, (system_id64,) in enumerate(station_systems):
        if i % 100 == 0:
            print(f"Processing {i}/{total_systems} systems...")

        try:
            # Check if system is already in PopulatedSystem
            existing = session.query(PopulatedSystem).filter(
                PopulatedSystem.id64 == system_id64
            ).one_or_none()

            if existing:
                already_exists += 1
                continue

            # Get system data from System table
            try:
                system = session.query(System).filter(
                    System.id64 == system_id64
                ).one()

                # Create new PopulatedSystem entry
                populated_system = PopulatedSystem(
                    id64=system.id64,
                    name=system.name,
                    coords=system.coords,
                    # Default controlling faction as empty JSON
                    controllingFaction={},
                    date=datetime.now()
                )

                session.add(populated_system)
                session.flush()
                transaction.commit()
                added += 1

            except NoResultFound:
                print(f"Warning: Station references system ID64 {system_id64} that doesn't exist in System table")
                errors += 1

        except IntegrityError:
            transaction.abort()
            errors += 1
            print(f"IntegrityError when adding system ID64 {system_id64}")
        except Exception as e:
            transaction.abort()
            errors += 1
            print(f"Error processing system ID64 {system_id64}: {str(e)}")

    print(f"\nSynchronization completed at {datetime.now()}")
    print(f"Summary:")
    print(f"  - Total systems with stations: {total_systems}")
    print(f"  - Already in PopulatedSystem: {already_exists}")
    print(f"  - Added to PopulatedSystem: {added}")
    print(f"  - Errors: {errors}")


if __name__ == '__main__':
    main()