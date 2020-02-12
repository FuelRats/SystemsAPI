Systems API
===========

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

- Initialize and upgrade the database using Alembic.

        env/bin/alembic -c development.ini upgrade unindexed

- Download and initialize the database

    env/bin/initialize_systems_api_db development.ini

- Inject the downloaded CSV files into your postgres database (Follow instructions from installer script)

- Start the EDDN listener

    python eddnclient.py development.ini

- Start the API

    env/bin/pserve development.ini
