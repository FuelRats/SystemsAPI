import requests
from urllib.parse import urljoin

_edsmURL = "https://www.edsm.net"
_edsmSystemURL = urljoin(_edsmURL, "/api-v1/system")
_edsmBodyURL = urljoin(_edsmURL, "/api-system-v1/bodies")
_edsmStationURL = urljoin(_edsmURL, "/api-system-v1/stations")


def edsm_query(url, params):
    """
    Fetch information from EDSM.
    :param url: The composed full URL of the EDSM API endpoint
    :param params: Query parameters to pass to the request
    :return: JSON, empty list or error message in JSON format.
    """
    try:
        r = requests.get(url, params=params)
        return r.json()
    except requests.exceptions.HTTPError as error:
        return f"{'Error': 'HTTP error: {error}'}"


def fetch_edsm_system_by_id(systemId):
    """
    Fetches a system JSON from EDSM by its EDSM ID.
    :param systemId: The system ID. NOT Id64!
    :return: JSON, or empty list
    """
    query = {'systemId': systemId,  'showId': 1, 'showCoordinates': 1, 'showInformation': 1, 'showPermit': 1}
    return edsm_query(_edsmSystemURL, query)


def fetch_edsm_system_by_name(systemName):
    """
    Fetches a system JSON from EDSM
    :param systemName: The system name
    :return: JSON with system info or None
    """
    query = {'systemName': systemName, 'showId': 1, 'showCoordinates': 1, 'showInformation': 1, 'showPermit':1}
    return edsm_query(_edsmSystemURL, query)


def fetch_edsm_bodies_by_name(systemName):
    """
    Fetches a system body JSON by its name. Please avoid this, use a KNOWN EDSM systemID instead.
    :param systemName: The system name
    :return: JSON with body info or empty list
    """
    query = {'systemName': systemName}
    return edsm_query(_edsmBodyURL, query)


def fetch_edsm_bodies_by_id(systemId):
    """
    Fetches a system body JSON by its EDSM id.
    :param systemId: The EDSM system ID. NOT the id64!
    :return: JSON with body info or empty list
    """
    query = {'systemId': systemId}
    return edsm_query(_edsmBodyURL, query)


def fetch_edsm_stations_by_id(systemId):
    """
    Fetches a systems stations JSON by its EDSM id.
    :param systemId: The EDSM system ID. NOT the id64!
    :return: JSON with station info or empty list
    """
    query = {'systemId': systemId}
    return edsm_query(_edsmStationURL, query)
