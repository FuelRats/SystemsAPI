Systems API
===========

Requirements
---------------

- Python >3.6 with python-dev installed.
- Postgresql >10 with dev headers, and extensions pg_trgm and fuzzystrmatch enabled.
- About 200GB of disk space. This will grow with time as the galaxy DB grows.

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

- Copy development.ini or production.ini to a different filename and configure according to your
  setup.

    cp development.ini run.ini

- Initialize and upgrade the database using Alembic.

        env/bin/alembic -c <yourfile.ini> upgrade unindexed

- Download and initialize the database

    env/bin/initialize_systems_api_db <yourfile.ini>

- Inject the downloaded CSV files into your postgres database (Follow instructions from installer script)

- Start the EDDN listener

    python eddnclient.py <yourfile.ini>

- Start the API

    env/bin/pserve <yourfile.ini>
