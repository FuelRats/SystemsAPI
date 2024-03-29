import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.txt')) as f:
    README = f.read()
with open(os.path.join(here, 'CHANGES.txt')) as f:
    CHANGES = f.read()

requires = [
    'plaster_pastedeploy',
    'pyramid',
    'pyramid_jinja2',
    'pyramid_debugtoolbar',
    'waitress',
    'alembic',
    'pyramid_retry',
    'pyramid_tm',
    'SQLAlchemy',
    'transaction',
    'zope.sqlalchemy',
    'psycopg2-binary',
    'requests',
    'zmq',
    'simplejson',
    'pyramid_jsonapi',
    'wget',
    'semver',
    'colander',
    'deform',
    'numpy',
    'plotly',
    'bigjson',
]

tests_require = [
    'WebTest >= 1.3.1',  # py3 compat
    'pytest >= 3.7.4',
    'pytest-cov',
]

setup(
    name='systems_api',
    version='1.0.5',
    description='Systems API',
    long_description=README + '\n\n' + CHANGES,
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Pyramid',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: WSGI :: Application',
    ],
    author='Absolver (Kenneth Aalberg)',
    author_email='absolver@fuelrats.com',
    url='https://github.com/Fuelrats/',
    keywords='web pyramid pylons api jsonapi fuelrats',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    extras_require={
        'testing': tests_require,
    },
    install_requires=requires,
    entry_points={
        'paste.app_factory': [
            'main = systems_api:main',
        ],
        'console_scripts': [
            'initialize_systems_api_db=systems_api.scripts.initialize_db:main',
            'generate_heatmap=systems_api.scripts.generate_heatmap:main',
            'load_edsmstations=systems_api.scripts.load_edsmstations:main',
        ],
    },
)
