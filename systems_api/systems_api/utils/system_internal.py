import math
import struct

from .pgnames import get_system as pg_get_system
from .pgnames import get_system_fragments as pg_get_system_fragments
from .pgnames import get_sector as pg_get_sector
from .pgnames import get_boxel_origin as pg_get_boxel_origin
from . import sector
from . import util
from . import vector3

class Body(object):
  STAR       = 1 << 0

  def __init__(self, body_type = None, name = None):
    self.type = body_type
    self.name = name

  def to_opaq(self):
    return {
      'name': self.name,
      'type': 'body'
    }


class Star(Body):
  MAIN_SEQUENCE   = ('O', 'B', 'A', 'F', 'G', 'K', 'M')
  BLACK_HOLE      = ('BH', 'SMBH')
  NEUTRON         = 'N'
  EXOTIC          = 'X'
  NON_SEQUENCE    = (BLACK_HOLE, EXOTIC, NEUTRON)
  SCOOPABLE       = MAIN_SEQUENCE
  SUPERCHARGEABLE = ('D', NEUTRON)

  CLASS_NAMES     = {
    'A': 'A (blue-white) star',
    'AEBE': 'Herbig Ae/Be star',
    'B': 'B (blue-white) star',
    'C': 'C star',
    'CH': 'CH star',
    'CHD': 'Chd star',
    'CJ': 'CJ star',
    'CN': 'CN star',
    'CS': 'CS star',
    'D': 'D (white dwarf) star',
    'DA': 'DA (white dwarf) star',
    'DAB': 'DAB (white dwarf) star',
    'DAO': 'DAO (white dwarf) star',
    'DAV': 'DAV (white dwarf) star',
    'DAZ': 'DAZ (white dwarf) star',
    'DB': 'DB (white dwarf) star',
    'DBV': 'DBV (white dwarf) star',
    'DBZ': 'DBZ (white dwarf) star',
    'DC': 'DC (white dwarf) star',
    'DCV': 'DCV (white dwarf) star',
    'DO': 'DO (white dwarf) star',
    'DOV': 'DOV (white dwarf) star',
    'DQ': 'DQ (white dwarf) star',
    'DX': 'DX (white dwarf) star',
    'F': 'F (white) star',
    'G': 'G (white-yellow) star',
    'H': 'Black hole',
    'K': 'K (yellow-orange) star',
    'L': 'L (brown dwarf) star',
    'M': 'M (red) star',
    'MS': 'MS star',
    'N': 'Neutron star',
    'O': 'O (blue-white) star',
    'S': 'S star',
    'SMBH': 'Supermassive black hole',
    'T': 'T (brown dwarf) star',
    'TTS': 'T Tauri star',
    'W': 'Wolf-Rayet star',
    'WC': 'Wolf-Rayet C star',
    'WN': 'Wolf-Rayet N star',
    'WNC': 'Wolf-Rayet NC star',
    'WO': 'Wolf-Rayet O star',
    'X': 'Exotic star',
    'Y': 'Y (brown dwarf) star'
  }

  EDSM_CLASS_NAMES = {
    "A (Blue-White super giant) Star": "A",
    "A (Blue-White) Star": "A",
    "B (Blue-White) Star": "B",
    "Black Hole": "BH",
    "C Star": "C",
    "CH Star": "CH",
    "CHd Star": "CHD",
    "CJ Star": "CJ",
    "CN Star": "CN",
    "CS Star": "CS",
    "F (White super giant) Star": "F",
    "F (White) Star": "F",
    "G (White-Yellow) Star": "G",
    "Herbig Ae/Be Star": "AEBE",
    "K (Yellow-Orange giant) Star": "K",
    "K (Yellow-Orange) Star": "K",
    "L (Brown dwarf) Star": "L",
    "M (Red dwarf) Star": "M",
    "M (Red giant) Star": "M",
    "M (Red super giant) Star": "M",
    "MS-type Star": "MS",
    "Neutron Star": "N",
    "O (Blue-White) Star": "O",
    "S-type Star": "S",
    "Supermassive Black Hole": "SMBH",
    "T (Brown dwarf) Star": "T",
    "T Tauri Star": "TTS",
    "White Dwarf (D) Star": "D",
    "White Dwarf (DA) Star": "DA",
    "White Dwarf (DAB) Star": "DAB",
    "White Dwarf (DAO) Star": "DAO",
    "White Dwarf (DAV) Star": "DAV",
    "White Dwarf (DAZ) Star": "DAZ",
    "White Dwarf (DB) Star": "DB",
    "White Dwarf (DBV) Star": "DBV",
    "White Dwarf (DBZ) Star": "DBZ",
    "White Dwarf (DC) Star": "DC",
    "White Dwarf (DCV) Star": "DCV",
    "White Dwarf (DO) Star": "DO",
    "White Dwarf (DOV) Star": "DOV",
    "White Dwarf (DQ) Star": "DQ",
    "White Dwarf (DX) Star": "DX",
    "Wolf-Rayet C Star": "WC",
    "Wolf-Rayet N Star": "WN",
    "Wolf-Rayet NC Star": "WNC",
    "Wolf-Rayet O Star": "WO",
    "Wolf-Rayet Star": "W",
    "X": "X",
    "Y (Brown dwarf) Star": "Y"
  }

class System(object):
    """A single star system."""

    def __init__(self, x, y, z, name=None, id64=None, uncertainty=0.0):
        """
        Create a base system object.

        Args:
          x: The in-game system position in the x axis
          y: The in-game system position in the y axis
          z: The in-game system position in the z axis
          name: The system's name, or none if it is not known
          id64: The system's id64 ("system address"), or none if it is not known
          uncertainty: The uncertainty in the position provided, in each axis
        """
        self._position = vector3.Vector3(float(x), float(y), float(z))
        self._name = name
        self._id = None
        self._id64 = id64
        self._uncertainty = uncertainty
        self.uses_sc = False
        self._hash = u"{}/{},{},{}".format(self.name, self.position.x, self.position.y, self.position.z).__hash__()
        self._arrival_star = Star({'name': name, 'is_main_star': True, })

    @property
    def system_name(self):
        """The system's name, or None if this is not available"""
        return self.name

    @property
    def position(self):
        """The system's in-game position"""
        return self._position

    @property
    def name(self):
        """The system's name, or None if this is not available"""
        return self._name

    @property
    def pg_name(self):
        """The system's name as determined by the game's procedural generation system, or None if this is not available"""
        if self.id64 is not None:
            coords, cube_width, n2, _ = calculate_from_id64(self.id64)
            sys_proto = pg_get_system(coords, cube_width, allow_ha=False)
            return sys_proto.name + str(n2)
        else:
            return None

    @property
    def id(self):
        """The system's ID as specified by the data source used to import it, or None if this is not available"""
        return self._id

    @property
    def id64(self):
        """The system's ID64 ("system address") as a 64-bit integer, or None if it is not available"""
        if self._id64 is None:
            if self.name is not None:
                m = pg_get_system_fragments(self.name)
                if m is not None:
                    self._id64 = calculate_id64(self.position, m['MCode'], m['N2'])
        return self._id64

    @property
    def sector(self):
        """The sector or region this system falls within"""
        return pg_get_sector(self.position)

    @property
    def pg_sector(self):
        """The procedurally-generated sector which this system falls within"""
        return pg_get_sector(self.position, allow_ha=False)

    @property
    def needs_permit(self):
        """Whether or not this system or the region it is within needs a permit to enter"""
        return self.sector.needs_permit

    @property
    def needs_system_permit(self):
        """Whether or not this system specifically needs a permit to enter"""
        return False

    @property
    def uncertainty(self):
        """The uncertainty per axis of this system's position"""
        return self._uncertainty

    @property
    def uncertainty3d(self):
        """The maximum uncertainty (straight-line distance) of this system's position"""
        return math.sqrt((self.uncertainty ** 2) * 3)

    @property
    def arrival_star_class(self):
        """The class of the system's arrival star, or None if it is not available"""
        return self.arrival_star.classification

    @property
    def arrival_star(self):
        """A Star object representing the system's arrival star, or None if it is not available"""
        return self._arrival_star

    def to_string(self, use_long=False):
        """
        Describes this system as a string.

        Args:
          use_long: If true, also includes the system position
        Returns:
          A string representing this system
        """
        if use_long:
            return u"{0} ([{1:.2f}, {2:.2f}, {3:.2f}])".format(self.name, self.position.x, self.position.y,
                                                               self.position.z)
        else:
            return self.name

    def __str__(self):
        return self.to_string()

    def __repr__(self):
        return u"System({})".format(self.name)

    def to_opaq(self):
        return {
            'name': self.name,
            'id64': self.id64,
            'arrival_star': self.arrival_star,
            'position': self.position,
            'uncertainty': self.uncertainty
        }

    def distance_to(self, other):
        """
        Gets the distance between this system and another system or position

        Args:
          other: The other point to get distance to. May be a system object, a vector or an x,y,z tuple
        Returns:
          The distance in light years between this system and the other point
        """
        other = util.get_as_position(other)
        if other is not None:
            return (self.position - other).length
        else:
            raise ValueError("distance_to argument must be position-like object")

    def __eq__(self, other):
        if isinstance(other, System):
            return (self.name == other.name and self.position == other.position)
        else:
            return NotImplemented

    def pretty_id64(self, fmt='INT'):
        """
        Gets the system's ID64 in a prettified format.

        Args:
          fmt: The format to return. May be 'INT' for an integer, 'HEX' for big-endian hex or 'VSC' for little-endian hex with spacing
        Returns:
          A string representing the system's ID64 in the chosen format
        """
        if self.id64 is None:
            return "MISSING ID64"
        if fmt == 'VSC':
            return ' '.join('{0:02X}'.format(b) for b in bytearray(struct.pack('<Q', self.id64)))
        else:
            return ("{0:016X}" if fmt == 'HEX' else "{0:d}").format(self.id64)

    def __hash__(self):
        return self._hash


class PGSystemPrototype(System):
    """A procedurally-generated system with unknown N2 - a single unknown system with estimated coordinates."""

    def __init__(self, x, y, z, name, sector, uncertainty):
        """
        Creates an unknown system object within a known boxel

        Args:
          x: The in-game system position in the x axis
          y: The in-game system position in the y axis
          z: The in-game system position in the z axis
          name: The system's name, or none if it is not known
          sector: The sector this system falls within
          uncertainty: The uncertainty in the position provided, in each axis
        """
        super(PGSystemPrototype, self).__init__(x, y, z, name, uncertainty=uncertainty)
        self._sector = sector

    @property
    def sector(self):
        return self._sector

    def __repr__(self):
        return u"PGSystemPrototype({})".format(
            self.name if self.name is not None else '{},{},{}'.format(self.position.x, self.position.y,
                                                                      self.position.z))

    def __hash__(self):
        return super(PGSystemPrototype, self).__hash__()


class PGSystem(PGSystemPrototype):
    """A procedurally-generated system with estimated coordinates."""

    def __init__(self, x, y, z, name, sector, uncertainty):
        """
        Creates a PG system object within a known boxel

        Args:
          x: The in-game system position in the x axis
          y: The in-game system position in the y axis
          z: The in-game system position in the z axis
          name: The system's name, or none if it is not known
          sector: The sector this system falls within
          uncertainty: The uncertainty in the position provided, in each axis
        """
        super(PGSystem, self).__init__(x, y, z, name, sector, uncertainty)

    def __repr__(self):
        return u"PGSystem({})".format(
            self.name if self.name is not None else '{},{},{}'.format(self.position.x, self.position.y,
                                                                      self.position.z))

    def __hash__(self):
        return super(PGSystem, self).__hash__()


class HASystem(System):
    """A hand-authored system with estimated coordinates."""

    def __init__(self, x, y, z, name, id64, uncertainty):
        """
        Creates an HA system without known coordinates.

        Args:
          x: The in-game system position in the x axis
          y: The in-game system position in the y axis
          z: The in-game system position in the z axis
          name: The system's name, or none if it is not known
          id64: The system's id64 ("system address"), or none if it is not known
          uncertainty: The uncertainty in the position provided, in each axis
        """
        super(HASystem, self).__init__(x, y, z, name, id64, uncertainty)

    def __repr__(self):
        return u"HASystem({})".format(
            self.name if self.name is not None else '{},{},{}'.format(self.position.x, self.position.y,
                                                                      self.position.z))

    def __hash__(self):
        return super(HASystem, self).__hash__()


class KnownSystem(System):
    """A known system with recorded coordinates and additional data."""

    def __init__(self, obj):
        """
        Creates a system object with data from a coordinates database.

        Args:
          obj: A dict containing the keys (x, y, z, name, id64), and optionally (id, needs_permit, allegiance, arrival_star_class)
        """
        super(KnownSystem, self).__init__(float(obj['x']), float(obj['y']), float(obj['z']), obj['name'], obj['id64'],
                                          0.0)
        self._id = obj['id'] if 'id' in obj else None
        self._needs_permit = obj['needs_permit'] if 'needs_permit' in obj else None
        self._allegiance = obj['allegiance'] if 'allegiance' in obj else None
        self._arrival_star = Star(
            {'name': obj['name'], 'is_main_star': True, 'spectral_class': obj.get('arrival_star_class')})

    @property
    def needs_permit(self):
        return (self.needs_system_permit or self.sector.needs_permit)

    @property
    def needs_system_permit(self):
        return self._needs_permit

    @property
    def allegiance(self):
        """The superpower allegiance of this system, or None if it is not available"""
        return self._allegiance

    def to_string(self, use_long=False):
        if use_long:
            return u"{0} ([{1:.2f}, {2:.2f}, {3:.2f}] {4})".format(self.name, self.position.x, self.position.y,
                                                                   self.position.z,
                                                                   self.arrival_star.to_string(use_long))
        else:
            return u"{0} ({1})".format(self.name, self.arrival_star.to_string(use_long))

    def __repr__(self):
        return u"KnownSystem({0})".format(self.name)

    def __eq__(self, other):
        if isinstance(other, KnownSystem):
            return ((
                                self.id is None or other.id is None or self.id == other.id) and self.name == other.name and self.position == other.position)
        elif isinstance(other, System):
            return super(KnownSystem, self).__eq__(other)
        else:
            return NotImplemented

    def __hash__(self):
        return super(KnownSystem, self).__hash__()


#
# System ID calculations
#

def mask_id64_as_system(i):
    """
    Given an ID64, masks the bits such that the body ID is zero, making it now only refer to a system

    Args:
      i: The ID64 to mask
    Returns:
      The masked ID64
    """
    result = i
    if util.is_str(result):
        result = int(result, 16)
    result &= (2 ** 55) - 1
    return result


def mask_id64_as_body(i):
    """
    Given an ID64, extracts the body ID and returns it as an integer. Note that the body ID's position in the bitfield is not retained.

    Args:
      i: The ID64 to mask
    Returns:
      The body ID of the ID64
    """
    result = i
    if util.is_str(result):
        result = int(result, 16)
    result >>= 55
    result &= (2 ** 9) - 1
    return result


def mask_id64_as_boxel(i):
    """
    Given an ID64, masks the bits such that the N2 and body ID are zero, making it refer to a boxel

    Args:
      i: The ID64 to mask
    Returns:
      The masked ID64
    """
    result = i
    if util.is_str(result):
        result = int(result, 16)
    numbits = 44 - 3 * (result & 2 ** 3 - 1)  # 44 - 3*mc
    result &= (2 ** numbits) - 1
    return result


def combine_to_id64(system, body):
    """
    Combines a system ID64 and body ID to create an ID64 representing that body

    Args:
      system: An ID64 representing a system
      body: A zero-indexed body ID
    Returns:
      A combined ID64 representing the specified body within the specified system
    """
    return (system & (2 ** 55 - 1)) + ((body & (2 ** 9 - 1)) << 55)


def calculate_from_id64(i):
    """
    Calculates a system's details from its ID64

    Args:
      i: A valid ID64
    Returns:
      A tuple of (estimated coordinates, boxel size, N2 number, body ID)
    """
    # If i is a string, assume hex
    if util.is_str(i):
        i = int(i, 16)
    # Calculate the shifts we need to do to get the individual fields out
    len_used = 0
    i, mc = util.unpack_and_shift(i, 3);
    len_used += 3  # mc = 0-7 for a-h
    i, boxel_z = util.unpack_and_shift(i, 7 - mc);
    len_used += 7 - mc
    i, sector_z = util.unpack_and_shift(i, 7);
    len_used += 7
    i, boxel_y = util.unpack_and_shift(i, 7 - mc);
    len_used += 7 - mc
    i, sector_y = util.unpack_and_shift(i, 6);
    len_used += 6
    i, boxel_x = util.unpack_and_shift(i, 7 - mc);
    len_used += 7 - mc
    i, sector_x = util.unpack_and_shift(i, 7);
    len_used += 7
    i, n2 = util.unpack_and_shift(i, 55 - len_used)
    i, body_id = util.unpack_and_shift(i, 9)
    # Multiply each X/Y/Z value by the cube width to get actual coords
    boxel_size = 10 * (2 ** mc)
    coord_x = (sector_x * sector.sector_size) + (boxel_x * boxel_size) + (boxel_size / 2)
    coord_y = (sector_y * sector.sector_size) + (boxel_y * boxel_size) + (boxel_size / 2)
    coord_z = (sector_z * sector.sector_size) + (boxel_z * boxel_size) + (boxel_size / 2)
    coords_internal = vector3.Vector3(coord_x, coord_y, coord_z)
    # Shift the coords to be the origin we know and love
    coords = coords_internal + sector.internal_origin_offset
    return (coords, boxel_size, n2, body_id)


def calculate_id64(pos, mcode, n2, body=0):
    """
    Calculates a system's ID64 from its details

    Args:
      pos: The system's position
      mcode: The mass code of the system, or its boxel size
      n2: The N2 number of the system
      body: The body ID of the body within the system, or zero to create an ID64 for a system
    Returns:
      The ID64 representing the specified system details
    """
    # Get the data we need to start with (mc as 0-7, cube width, boxel X/Y/Z coords)
    mc = ord(sector.get_mcode(mcode)) - ord('a')
    cube_width = sector.get_mcode_cube_width(mcode)
    boxel_coords = (pg_get_boxel_origin(pos, mcode) - sector.internal_origin_offset) / cube_width
    # Populate each field, shifting as required
    output = util.pack_and_shift(0, int(body), 9)
    output = util.pack_and_shift(output, int(n2), 11 + mc * 3)
    output = util.pack_and_shift(output, int(boxel_coords.x), 14 - mc)
    output = util.pack_and_shift(output, int(boxel_coords.y), 13 - mc)
    output = util.pack_and_shift(output, int(boxel_coords.z), 14 - mc)
    output = util.pack_and_shift(output, mc, 3)
    return output
