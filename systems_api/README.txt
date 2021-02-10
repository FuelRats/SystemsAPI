Systems API
===========

Requirements
---------------

- Python >3.6 with python-all-dev installed.
- Postgresql >10 with dev headers, and extensions pg_trgm and fuzzystrmatch enabled.
- About 200GB of disk space. This will grow with time as the galaxy DB grows.
- pgloader >3.6

Installing
---------------

- Change directory into your newly created project.

        cd systems_api

- Create a Python virtual environment.

        python3 -m venv env

- Upgrade packaging tools.

        env/bin/pip install --upgrade pip setuptools

- Install the project in editable mode with its testing requirements.

        env/bin/pip install -e ".[testing]"

- Copy development.ini.template or production.ini.template to a different filename
  and configure according to your setup.

        cp development.ini.template run.ini

- Copy pgloader.ini.template to pgloader.ini and configure. The DB URL should be the
  same as sqlalchemy.url in the main config file.  You probably want to adjust working
  memory to suit your system.

        cp pgloader.ini.template pgloader.ini

- Initialize and upgrade the database using Alembic.

        env/bin/alembic -c <yourfile.ini> upgrade unindexed

- Download and initialize the database

        env/bin/initialize_systems_api_db <yourfile.ini>

- Inject the downloaded CSV files into your postgres database using pgloader
  (Slower, but with error correction for problems in the CSV files)
        pgloader --context pgloader.ini systems.load
        pgloader --context pgloader.ini stars.load
        pgloader --context pgloader.ini populated.load
        pgloader --context pgloader.ini planets.load
    Add the -v flag if you want more verbose reporting on progress and performance.
  OR

  Load the downloaded CSV files into postgres using psql's COPY feature
  (Does not do any error detection, if there's a problem anywhere in the file,
  the whole insert will fail)


- Apply indexes to the database
        env/bin/alembic -c <yourfile.ini> upgrade indexes

- Start the EDDN listener (If you want live updates from EDDN. You probably do.)

        python systems_api/eddn_client.py <yourfile.ini>

- Start the API

        env/bin/pserve <yourfile.ini>


Contributions
--------------

Mostly written by Absolver.

PG system logic stolen from Esvandiary's EDTS project (https://bitbucket.org/Esvandiary/edts/).
Thanks to Alot/Esvandiary and Jackie Silver for their incredible work on figuring out how PG
systems are generated.
