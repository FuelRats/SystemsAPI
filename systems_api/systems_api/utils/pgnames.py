#
# This code was yeeted from Esvandiary's EDTS project
#

from __future__ import print_function, division
import collections
import string
import time

from . import pgdata
from . import sector
from . import util
from . import vector3

# #
# Publicly-useful functions
# #

def is_pg_system_name(name, strict=False):
    """
    Check whether the given name is a valid PG system name, either in a PG or HA sector.

    Args:
      name: A system name
      strict: If True, will also check the sector name is a valid sector.
    Returns:
      True if the name is valid, False if not
    """
    m = pgdata.pg_system_regex.match(name.strip())
    if m is None:
        return False
    return (get_sector(m.group("sector")) is not None) if strict else True


def get_sector_name(pos, allow_ha=True, format_output=True):
    """
    Get the name of a sector that a position falls within.

    Args:
      pos: A position
      format_output: Whether or not to format the output or return it as fragments
    Returns:
      The name of the sector which contains the input position, either as a string or as a list of fragments
    """
    pos = util.get_as_position(pos)
    if pos is None:
        return None
    if allow_ha:
        ha_name = _ha_get_name(pos)
        if ha_name is not None:
            return ha_name
    offset = _c1_get_offset(pos)
    if _get_c1_or_c2(offset) == 1:
        output = _c1_get_name(pos)
    else:
        output = _c2_get_name(pos)

    if format_output:
        return format_sector_name(output)
    else:
        return output


def get_sector(input, allow_ha=True, get_name=True):
    """
    Get a Sector object represented by a name, or which a position falls within.

    Args:
      input: A sector name, or a position
      allow_ha: Whether to include hand-authored sectors in the search
      get_name: Whether to look up the name of the sector
    Returns:
      A Sector object, or None if the input could not be looked up
    """
    pos_input = util.get_as_position(input)
    if pos_input is not None:
        input = pos_input
        if allow_ha:
            ha_name = _ha_get_name(input)
            if ha_name is not None:
                return pgdata.ha_regions[ha_name.lower()]
        # If we're not checking HA or it's not in such a sector, do PG
        x = (input.x - sector.base_coords.x) // sector.sector_size
        y = (input.y - sector.base_coords.y) // sector.sector_size
        z = (input.z - sector.base_coords.z) // sector.sector_size
        # Get the name, if we are
        frags = None
        if get_name:
            frags = get_sector_name(input, allow_ha=allow_ha, format_output=False)
        return sector.PGSector(int(x), int(y), int(z), format_sector_name(frags), _get_sector_class(frags))
    else:
        # Assume we have a string, call down to get it by name
        return _get_sector_from_name(input, allow_ha=allow_ha)


def get_system(input, mcode=None, allow_ha=True):
    """
    Get a system object based on its name or position

    Args:
      input: The system's name or position
      mcode: The system's mass code ('a'-'h') or cube side length; only required when input is a position
    Returns:
      A system or system prototype object
    """
    posinput = util.get_as_position(input)
    if posinput is not None:
        if mcode is not None:
            return _get_system_from_pos(posinput, mcode, allow_ha)
        else:
            raise ValueError("mcode argument must be provided to get_system if input is a position")
    else:
        return _get_system_from_name(input, allow_ha)


def get_canonical_name(name, sector_only=False):
    """
    Get the correctly-cased name for a given sector or system name

    Args:
      name: A system or sector name, in any case
    Returns:
      The input system/sector name with its case corrected
    """
    result = _get_canonical_name_fragments(name, sector_only)
    if result is None or 'SectorName' not in result:
        return None
    return format_system_name(result) if (len(result) > 1 and not sector_only) else result['SectorName']


def get_sector_fragments(sector_name, allow_long=False):
    """
    Get a list of fragments from an input sector name
    e.g. "Dryau Aowsy" --> ["Dry","au","Ao","wsy"]

    Args:
      sector_name: The name of the sector
      allow_long: Whether to allow sector names longer than the usual maximum fragment count (4)
    Returns:
      A list of fragments representing the sector name
    """
    # Convert the string to Title Case, then remove spaces
    sector_name = sector_name.title().replace(' ', '')
    segments = []
    current_str = sector_name
    while len(current_str) > 0:
        found = False
        for frag in pgdata.cx_fragments:
            if current_str[0:len(frag)] == frag:
                segments.append(frag)
                current_str = current_str[len(frag):]
                found = True
                break
        if not found:
            break
    if len(current_str) == 0 and (allow_long or len(segments) <= _expected_fragment_limit):
        return segments
    else:
        return None


def is_valid_sector_name(input):
    """
    Checks whether or not the provided sector name is a valid PG name

    Mild weakness: due to the way get_sector_fragments works, this currently ignores all spaces
    This means that names like "Synoo kio" are considered valid

    Args:
      input: A candidate sector name
    Returns:
      True if the sector name is valid, False if not
    """
    frags = get_sector_fragments(input) if util.is_str(input) else input
    if frags is None or len(frags) == 0 or frags[0] not in pgdata.cx_prefixes:
        return False
    if len(frags) == 4 and frags[2] in pgdata.cx_prefixes:
        # Class 2
        f1idx = pgdata.c2_prefix_suffix_override_map.get(frags[0], 1)
        f3idx = pgdata.c2_prefix_suffix_override_map.get(frags[2], 1)
        return (frags[1] in pgdata.c2_suffixes[f1idx] and frags[3] in pgdata.c2_suffixes[f3idx])
    elif len(frags) in [3, 4]:
        # Class 1
        fli_idx = pgdata.c1_prefix_infix_override_map.get(frags[0], 1)
        if frags[1] not in pgdata.c1_infixes[fli_idx]:
            return False
        if len(frags) == 4:
            fli_idx = 2 if fli_idx == 1 else 1
            if frags[2] not in pgdata.c1_infixes[fli_idx]:
                return False
        flastidx = 2 if fli_idx == 1 else 1
        return (frags[-1] in pgdata.c1_suffixes[flastidx])
    else:
        # Class NOPE
        return False


def format_sector_name(input):
    """
    Format a given set of fragments into a full name

    Args:
      input: A list of sector name fragments
    Returns:
      The sector name as a string
    """
    frags = get_sector_fragments(input) if util.is_str(input) else input
    if frags is None:
        return None
    if len(frags) == 4 and frags[2] in pgdata.cx_prefixes:
        return "{0}{1} {2}{3}".format(*frags)
    else:
        return "".join(frags)


def get_boxel_origin(position, mcode):
    """
    Get the origin of the boxel (cube) that the given coordinates sit within

    Args:
      position: A vector or tuple of X/Y/Z coordinates, or a System object
      mcode: The system's mass code ('a'-'h') or cube side length
    Returns:
      A Vector3 representing the origin of the boxel containing this position
    """
    posinput = util.get_as_position(position)
    cube_width = sector.get_mcode_cube_width(mcode)
    if posinput is None or cube_width is None:
        return None
    x = posinput.x - ((posinput.x - sector.internal_origin_offset.x) % cube_width)
    y = posinput.y - ((posinput.y - sector.internal_origin_offset.y) % cube_width)
    z = posinput.z - ((posinput.z - sector.internal_origin_offset.z) % cube_width)
    return vector3.Vector3(x, y, z)


def get_system_fragments(input, ensure_canonical=True):
    """
    Parse the given PG system name and return the canonical versions of its individual components

    Args:
      input: A string containing a system name of the form "Sector AB-C d1-23" or "Sector AB-C d1"
      ensure_canonical: Whether to ensure that the name is in its canonical form before processing
    Returns:
      A dictionary containing keys of SectorName, L1, L2, L3, MCode, N1 and N2
    """
    if ensure_canonical:
        return _get_canonical_name_fragments(input)
    m = pgdata.pg_system_regex.match(input)
    if m is None:
        return None
    return {
        'SectorName': m.group('sector'), 'L1': m.group('l1'), 'L2': m.group('l2'), 'L3': m.group('l3'),
        'MCode': m.group('mcode'), 'N1': int(m.group('n1')) if m.group('n1') is not None else 0,
        'N2': int(m.group('n2'))
    }


def format_system_name(input):
    """
    Format the given system data into a full name

    Args:
      input: A dictionary containing keys of SectorName, L1, L2, L3, MCode, N1 and N2
    Returns:
      A string containing a system name of the form "Sector AB-C d1-23" or "Sector AB-C d1"
    """
    if input is None:
        return None
    if not isinstance(input, dict) or not set(('SectorName', 'L1', 'L2', 'L3', 'MCode', 'N1', 'N2')).issubset(input):
        raise ValueError("input dict to format_system_name must include keys SectorName, L1, L2, L3, MCode, N1, N2")
    if input['N1'] is not None and int(input['N1']) != 0:
        sysid = "{}{}-{} {}{}-{}".format(input['L1'].upper(), input['L2'].upper(), input['L3'].upper(),
                                         input['MCode'].lower(), input['N1'], input['N2'])
    else:
        sysid = "{}{}-{} {}{}".format(input['L1'].upper(), input['L2'].upper(), input['L3'].upper(),
                                      input['MCode'].lower(), input['N2'])
    return "{} {}".format(input['SectorName'], sysid)


def get_ha_regions(reference=None, max_distance=None):
    """
    Get hand-authored sectors, optionally in distance order around a reference point

    Args:
      reference: Optional, position or System/Sector-like object. If provided, returned sectors will be ordered by distance from this point
      max_distance: Optional, may only be provided with reference. A maximum distance from the reference point, in LY, to limit returned sectors to.
    Returns:
      An OrderedDict object where keys are the names of the sectors, and values are the sector objects themselves.
    """
    if reference is not None:
        pos_reference = util.get_as_position(reference)
        if pos_reference is None:
            raise ValueError("if provided, reference must be a position, or a System/Sector-like object")
        result = [(s.name, s) for s in pgdata.ha_regions.values() if
                  (max_distance is None or (pos_reference - s.centre).length < max_distance)]
        result.sort(key=lambda s: (pos_reference - s[1].centre).length)
        return collections.OrderedDict(result)
    else:
        if max_distance is not None:
            raise ValueError("cannot provide max_distance without a reference position")
        return collections.OrderedDict([(s.name, s) for s in pgdata.ha_regions.values()])


# Alias for backwards compatibility
get_ha_sectors = get_ha_regions


def get_grid_coords(pos, mcode):
    """
    Get the grid (1/32LY) coordinates for the given position.

    Args:
      pos: The position to get the grid position for.
      mcode: The mass code to return the relative boxel coords for, or None to get global coords
    Returns:
      A tuple of the grid position in (x, y, z) form.
    """
    pos = util.get_as_position(pos)
    if pos is None:
        return None
    origin = sector.internal_origin_offset if not mcode else get_boxel_origin(pos, mcode)
    mx = int(round((pos.x - origin.x) * 32))
    my = int(round((pos.y - origin.y) * 32))
    mz = int(round((pos.z - origin.z) * 32))
    return (mx, my, mz)


def get_closest_grid_position(pos):
    """
    Get the closest point on the PG (1/32LY) grid to the given position.

    Args:
      pos: The position to map
    Returns:
      The closest valid point on the grid
    """
    pos = util.get_as_position(pos)
    if pos is None:
        return None
    mx, my, mz = get_grid_coords(pos, None)  # get global coords
    return sector.internal_origin_offset + vector3.Vector3(mx / 32.0, my / 32.0, mz / 32.0)


# #
# Internal variables
# #

_srp_divisor1 = len(string.ascii_uppercase)
_srp_divisor2 = _srp_divisor1 ** 2
_srp_divisor3 = _srp_divisor1 ** 3
_srp_rowlength = 128
_srp_sidelength = _srp_rowlength ** 2
_expected_fragment_limit = 4

# #
# Internal functions: shared/HA
# #

from . import system_internal as system

# Get a system's relative position within a sector
# Original version by CMDR Jackie Silver
# Note that in the form "Sector AB-C d3", the "3" is number2, NOT number1 (which is 0)
def _get_relpos_from_sysid(prefix, centre, suffix, mcode, number1, number2):
    soffset = _get_soffset_from_sysid(prefix, centre, suffix, number1)
    pos, uncertainty = _get_relpos_from_soffset(soffset, mcode)
    return (pos, uncertainty)


def _get_soffset_from_sysid(prefix, centre, suffix, number1):
    if number1 is None:
        number1 = 0

    position = _srp_divisor3 * int(number1)
    position += _srp_divisor2 * (ord(suffix.upper()) - ord('A'))
    position += _srp_divisor1 * (ord(centre.upper()) - ord('A'))
    position += (ord(prefix.upper()) - ord('A'))
    return position


def _get_relpos_from_soffset(position, mcode):
    row = int(position // _srp_sidelength)
    position -= (row * _srp_sidelength)

    stack = int(position // _srp_rowlength)
    position -= (stack * _srp_rowlength)

    column = position

    cubeside = sector.get_mcode_cube_width(mcode)
    halfwidth = cubeside / 2

    approx_x = (column * cubeside) + halfwidth
    approx_y = (stack * cubeside) + halfwidth
    approx_z = (row * cubeside) + halfwidth

    return (vector3.Vector3(approx_x, approx_y, approx_z), halfwidth)


def _get_sysid_from_relpos(pos, mcode, format_output=False):
    soffset = _get_soffset_from_relpos(pos, mcode)
    return _get_sysid_from_soffset(soffset, mcode, format_output)


def _get_soffset_from_relpos(pos, mcode):
    pos = util.get_as_position(pos)
    if pos is None:
        return None
    cubeside = sector.get_mcode_cube_width(mcode)
    column = int(pos.x // cubeside)
    stack = int(pos.y // cubeside)
    row = int(pos.z // cubeside)

    position = column + (_srp_rowlength * stack) + (_srp_sidelength * row)
    return position


def _get_sysid_from_soffset(position, mcode, format_output=False):
    prefixn = int((position) % len(string.ascii_uppercase))
    centren = int((position // _srp_divisor1) % len(string.ascii_uppercase))
    suffixn = int((position // _srp_divisor2) % len(string.ascii_uppercase))
    number1 = int((position // _srp_divisor3))

    prefix = string.ascii_uppercase[prefixn]
    centre = string.ascii_uppercase[centren]
    suffix = string.ascii_uppercase[suffixn]

    if format_output:
        output = '{}{}-{} {}'.format(prefix, centre, suffix, sector.get_mcode(mcode))
        if number1 != 0:
            output += '{}-'.format(number1)
        return output
    else:
        return [prefix, centre, suffix, sector.get_mcode(mcode), number1]


# Get the canonical name fragments of a system/sector
def _get_canonical_name_fragments(name, sector_only=False):
    sectname = None

    # See if we have a full system name
    m = pgdata.pg_system_regex.match(name)
    if m is not None:
        sectname_raw = m.group("sector")
    elif sector_only:
        sectname_raw = name
    else:
        return None

    # Check if this sector name appears in ha_regions, pass it through the fragment process if not
    if sectname_raw.lower() in pgdata.ha_regions:
        sectname = pgdata.ha_regions[sectname_raw.lower()].name
    else:
        # get_sector_fragments converts to Title Case, so we don't need to
        frags = get_sector_fragments(sectname_raw)
        if frags is not None:
            sectname = format_sector_name(frags)

    # Work out what we should be returning, and do it
    if not sector_only and m is not None and sectname is not None:
        return {
            'SectorName': sectname,
            'L1': m.group('l1').upper(), 'L2': m.group('l2').upper(), 'L3': m.group('l3').upper(),
            'MCode': m.group('mcode').lower(),
            'N1': int(m.group('n1')) if m.group('n1') is not None else 0, 'N2': int(m.group('n2'))}
    else:
        # sectname may be none if get_sector_fragments/format_sector_name failed
        return {'SectorName': sectname}


# Get the class of the sector from its name
# e.g. Froawns = 1, Froadue = 1, Eos Aowsy = 2
def _get_sector_class(sect):
    if util.is_str(sect) and sect.lower() in pgdata.ha_regions:
        return "ha"
    frags = get_sector_fragments(sect) if util.is_str(sect) else sect
    if frags is not None and len(frags) == 4 and frags[0] in pgdata.cx_prefixes and frags[2] in pgdata.cx_prefixes:
        return 2
    elif frags is not None and len(frags) in [3, 4] and frags[0] in pgdata.cx_prefixes:
        return 1
    else:
        return None


# Get the full list of suffixes for a given set of fragments missing a suffix
# e.g. "Dryau Ao", "Ogair", "Wreg"
def _get_suffixes(input, get_all=False):
    frags = get_sector_fragments(input) if util.is_str(input) else input
    if frags is None:
        return None
    wordstart = frags[0]
    if frags[-1] in pgdata.cx_prefixes:
        # Append suffix straight onto a prefix (probably C2)
        suffix_map_idx = pgdata.c2_prefix_suffix_override_map.get(frags[-1], 1)
        result = pgdata.c2_suffixes[suffix_map_idx]
        wordstart = frags[-1]
    else:
        # Likely C1
        if frags[-1] in pgdata.c1_infixes[2]:
            # Last infix is consonant-ish, return the vowel-ish suffix list
            result = pgdata.c1_suffixes[1]
        else:
            result = pgdata.c1_suffixes[2]

    if get_all:
        return result
    else:
        return result[0: _get_prefix_run_length(wordstart)]


# Get the specified prefix's run length (e.g. Th => 35, Tz => 1)
def _get_prefix_run_length(frag):
    return pgdata.cx_prefix_length_overrides.get(frag, pgdata.cx_prefix_length_default)


def _get_entry_from_offset(offset, keys, data):
    return [c for c in keys if offset >= data[c][0] and offset < (data[c][0] + data[c][1])][0]


# Get the sector offset of a position
def _get_offset_from_pos(pos, galsize):
    sect = get_sector(pos, allow_ha=False, get_name=False) if not isinstance(pos, sector.PGSector) else pos
    offset = sect.index[2] * galsize[1] * galsize[0]
    offset += sect.index[1] * galsize[0]
    offset += sect.index[0]
    return offset


def _get_sector_pos_from_offset(offset, galsize):
    x = (offset % galsize[0])
    y = (offset // galsize[0]) % galsize[1]
    z = (offset // (galsize[0] * galsize[1]))
    # Put it in "our" coordinate space
    x -= sector.base_sector_index[0]
    y -= sector.base_sector_index[1]
    z -= sector.base_sector_index[2]
    return [x, y, z]


# Determines whether a given sector should be C1 or C2
def _get_c1_or_c2(key):
    # Use Jenkins hash
    key = util.jenkins32(key)
    # Key is now an even/odd number, depending on which scheme we use
    # Return 1 for a class 1 sector, 2 for a class 2
    return (key % 2) + 1


def _get_sector_from_name(sector_name, allow_ha=True):
    sector_name = get_canonical_name(sector_name, sector_only=True)
    if sector_name is None:
        return None
    if allow_ha and util.is_str(sector_name) and sector_name.lower() in pgdata.ha_regions:
        return pgdata.ha_regions[sector_name.lower()]
    else:
        frags = get_sector_fragments(sector_name) if util.is_str(sector_name) else sector_name
        if frags is not None:
            sc = _get_sector_class(frags)
            if sc == 2:
                # Class 2
                return _c2_get_sector(frags)
            elif sc == 1:
                # Class 1
                return _c1_get_sector(frags)
            else:
                return None
        else:
            return None


def _get_coords_from_name(raw_system_name, allow_ha=True):
    system_name = get_canonical_name(raw_system_name)
    if system_name is None:
        return (None, None)
    # Reparse it now it's (hopefully) right
    m = get_system_fragments(system_name)
    if m is None:
        return (None, None)
    sector_name = m['SectorName']
    sect = _get_sector_from_name(sector_name, allow_ha)
    if sect is None:
        return (None, None)
    # Get the absolute position of the sector
    abs_pos = sect.get_origin(sector.get_mcode_cube_width(m['MCode']))
    # Get the relative position of the star within the sector
    # Also get the +/- error bounds
    rel_pos, rel_pos_error = _get_relpos_from_sysid(m['L1'], m['L2'], m['L3'], m['MCode'], m['N1'], m['N2'])

    # Check if the relpos is invalid
    leeway = rel_pos_error if (sect.sector_class == 'ha') else 0
    if any([s > (sector.sector_size + leeway) for s in rel_pos]):
        return (None, None)

    if abs_pos is not None and rel_pos is not None:
        return (abs_pos + rel_pos, rel_pos_error)
    else:
        return (None, None)


def _get_system_from_pos(input, mcode, allow_ha=True):
    input = util.get_as_position(input)
    if input is None:
        return None
    psect = get_sector(input, allow_ha=allow_ha)
    # Get cube width for this mcode, and the sector origin
    cwidth = sector.get_mcode_cube_width(mcode)
    psorig = psect.get_origin(cwidth)
    # Get the relative inputition within this sector and the system identifier
    relpos = vector3.Vector3(input.x - psorig.x, input.y - psorig.y, input.z - psorig.z)
    sysid = _get_sysid_from_relpos(relpos, mcode, format_output=True)


def _get_system_from_name(input, allow_ha=True):
    m = get_system_fragments(input)
    if m is not None and m['SectorName'] is not None:

        sect = get_sector(m['SectorName'])
        rel_pos, uncertainty = _get_relpos_from_sysid(m['L1'], m['L2'], m['L3'], m['MCode'], m['N1'], m['N2'])
        if sect is not None and rel_pos is not None and uncertainty is not None:
            cube_width = sector.get_mcode_cube_width(m['MCode'])
            coords = sect.get_origin(cube_width) + rel_pos
            if allow_ha:
                return {'handauthored': True, 'coords': {'x': coords.x, 'y': coords.y, 'z': coords.z}, 'uncertainty': uncertainty}
            else:
                pg_sect = get_sector(coords, allow_ha=False)
                # Now subtract the coords from ye olde origin to get the real PG relpos
                sysid = _get_sysid_from_relpos(coords - pg_sect.get_origin(cube_width), m['MCode'], format_output=True)
                return {'handauthored': False, 'coords': {'x': coords.x, 'y': coords.y, 'z': coords.z}, 'uncertainty': uncertainty}
        else:
            return None
    else:
        return None


# Get which HA sector this position would be part of, if any
def _ha_get_name(pos):
    for (_, s) in pgdata.ha_regions.items():
        if s.contains(pos):
            return s.name
    return None


# #
# Internal functions: c1-specific
# #

# Get the full list of infixes for a given set of fragments missing an infix
# e.g. "Ogai", "Wre", "P"
def _c1_get_infixes(input):
    frags = get_sector_fragments(input) if util.is_str(input) else input
    if frags is None:
        return None
    if frags[-1] in pgdata.cx_prefixes:
        if frags[-1] in pgdata.c1_prefix_infix_override_map:
            return pgdata.c1_infixes[pgdata.c1_prefix_infix_override_map[frags[-1]]]
        else:
            return pgdata.c1_infixes[1]
    elif frags[-1] in pgdata.c1_infixes[1]:
        return pgdata.c1_infixes[2]
    elif frags[-1] in pgdata.c1_infixes[2]:
        return pgdata.c1_infixes[1]
    else:
        return None


# Get the specified infix's run length
def _c1_get_infix_run_length(frag):
    if frag in pgdata.c1_infixes_s1:
        def_len = pgdata.c1_infix_s1_length_default
    else:
        def_len = pgdata.c1_infix_s2_length_default
    return pgdata.c1_infix_length_overrides.get(frag, def_len)


# Get the total run length for the series of infixes the input is part of
def _c1_get_infix_total_run_length(frag):
    if frag in pgdata.c1_infixes_s1:
        return pgdata.c1_infix_s1_total_run_length
    else:
        return pgdata.c1_infix_s2_total_run_length


# Get the zero-based offset (counting from bottom-left of the galaxy) of the input sector name/position
def _c1_get_offset(input):
    pos_input = util.get_as_position(input)
    if pos_input is not None:
        return _get_offset_from_pos(pos_input, sector.galaxy_size)
    else:
        return _c1_get_offset_from_name(input)


def _c1_get_offset_from_name(input):
    frags = get_sector_fragments(input) if util.is_str(input) else input
    if frags is None:
        return None

    try:
        sufs = _get_suffixes(frags[0:-1], True)

        # STEP 1: Acquire the offset for suffix runs, and adjust it
        suf_offset = sufs.index(frags[-1])
        # Assume suffix is fragment 3 unless we override that
        f3_offset = suf_offset

        # Add the total length of all the infixes we've already passed over
        if len(frags) > 3:
            # We have a 4-phoneme name, which means we have to handle adjusting our "coordinates"
            # from individual suffix runs up to fragment3 runs and then to fragment2 runs

            # Check which fragment3 run we're on, and jump us up by that many total run lengths if not the first
            suf_offset += (sufs.index(frags[-1]) // _c1_get_infix_run_length(
                frags[2])) * _c1_get_infix_total_run_length(frags[2])

            # STEP 1.5: Take our current offset from "suffix space" to "fragment3 space"
            # Divide by the current fragment3's run length
            # Remember the offset that we're at on the current suffix-run
            f3_offset, f3_offset_mod = divmod(suf_offset, _c1_get_infix_run_length(frags[2]))
            # Multiply by the total run length for this series of fragment3s
            f3_offset *= _c1_get_infix_total_run_length(frags[2])
            # Reapply the f3 offset from earlier
            f3_offset += f3_offset_mod
            # Add the offset of the current fragment3, to give us our overall position in the f3-sequence
            f3_offset += _c1_infix_offsets[frags[2]][0]

        # STEP 2: Take our current offset from "fragment3 space" to "fragment2 space"
        # Divide by the current fragment2's run length
        # Remember the offset that we're at on the current f3-run
        f2_offset, f2_offset_mod = divmod(f3_offset, _c1_get_infix_run_length(frags[1]))
        # Multiply by the total run length for this series of fragment2s
        f2_offset *= _c1_get_infix_total_run_length(frags[1])
        # Reapply the f2 offset from earlier
        f2_offset += f2_offset_mod
        # Add the offset of the current fragment2, to give us our overall position in the f2-sequence
        f2_offset += _c1_infix_offsets[frags[1]][0]

        # Divide by the current prefix's run length, this is now how many iterations of the full 3037 we should have passed over
        # Also remember the current offset's position within a prefix run
        offset, offset_mod = divmod(f2_offset, _get_prefix_run_length(frags[0]))
        # Now multiply by the total run length (3037) to get the actual offset of this run
        offset *= pgdata.cx_prefix_total_run_length
        # Add the infixes/suffix's position within this prefix's part of the overall prefix run
        offset += offset_mod
        # Add the base position of this prefix within the run
        offset += _prefix_offsets[frags[0]][0]
        # Whew!
        return offset
    except:
        # Either the prefix or suffix lookup failed, likely a dodgy name
        return None


# Get the sector position of the given input class 1 sector name
def _c1_get_sector(input):
    frags = get_sector_fragments(input) if util.is_str(input) else input
    if frags is None:
        return None
    offset = _c1_get_offset(frags)
    if offset is None:
        return None

    # Calculate the X/Y/Z positions from the offset
    spos = _get_sector_pos_from_offset(offset, sector.galaxy_size)
    name = format_sector_name(frags)
    return sector.PGSector(spos[0], spos[1], spos[2], name, _get_sector_class(frags))


def _c1_get_name(pos):
    if pos is None:
        return None
    offset = _c1_get_offset(pos)

    # Get the current prefix run we're on, and keep the remaining offset
    prefix_cnt, cur_offset = divmod(offset, pgdata.cx_prefix_total_run_length)
    # Work out which prefix we're currently within
    prefix = _get_entry_from_offset(cur_offset, _prefix_offsets, _prefix_offsets)
    # Put us in that prefix's space
    cur_offset -= _prefix_offsets[prefix][0]

    # Work out which set of infix1s we should be using, and its total length
    infix1s = _c1_get_infixes([prefix])
    infix1_total_len = _c1_get_infix_total_run_length(infix1s[0])
    # Work out where we are in infix1 space, keep the remaining offset
    infix1_cnt, cur_offset = divmod(prefix_cnt * _get_prefix_run_length(prefix) + cur_offset, infix1_total_len)
    # Find which infix1 we're currently in
    infix1 = _get_entry_from_offset(cur_offset, infix1s, _c1_infix_offsets)
    # Put us in that infix1's space
    cur_offset -= _c1_infix_offsets[infix1][0]

    # Work out which set of suffixes we're using
    infix1_run_len = _c1_get_infix_run_length(infix1)
    sufs = _get_suffixes([prefix, infix1], True)
    # Get the index of the next entry in that list, in infix1 space
    next_idx = (infix1_run_len * infix1_cnt) + cur_offset

    # Start creating our output
    frags = [prefix, infix1]

    # If the index of the next entry is longer than the list of suffixes...
    # This means we've gone over all the 3-phoneme names and started the 4-phoneme ones
    # So, we need to calculate our extra phoneme (infix2) before adding a suffix
    if next_idx >= len(sufs):
        # Work out which set of infix2s we should be using
        infix2s = _c1_get_infixes(frags)
        infix2_total_len = _c1_get_infix_total_run_length(infix2s[0])
        # Work out where we are in infix2 space, still keep the remaining offset
        infix2_cnt, cur_offset = divmod(infix1_cnt * _c1_get_infix_run_length(infix1) + cur_offset, infix2_total_len)
        # Find which infix2 we're currently in
        infix2 = _get_entry_from_offset(cur_offset, infix2s, _c1_infix_offsets)
        # Put us in this infix2's space
        cur_offset -= _c1_infix_offsets[infix2][0]

        # Recalculate the next system index based on the infix2 data
        infix2_run_len = _c1_get_infix_run_length(infix2)
        sufs = _get_suffixes([prefix, infix1, infix2], True)
        next_idx = (infix2_run_len * infix2_cnt) + cur_offset

        # Add our infix2 to the output
        frags.append(infix2)

    # Add our suffix to the output, and return it
    frags.append(sufs[next_idx])
    return frags


# #
# Internal functions: c2-specific
# #

# Get the name of a class 2 sector based on its position
def _c2_get_name(pos):
    offset = _get_offset_from_pos(pos, sector.galaxy_size)
    return _c2_get_name_from_offset(offset)


# Get the sector position of the given input class 2 sector name
def _c2_get_sector(input):
    frags = get_sector_fragments(input) if util.is_str(input) else input
    if frags is None:
        return None
    offset = _c2_get_offset_from_name(frags)
    if offset is None:
        return None

    # Calculate the X/Y/Z positions from the offset
    spos = _get_sector_pos_from_offset(offset, sector.galaxy_size)
    name = format_sector_name(frags)
    return sector.PGSector(spos[0], spos[1], spos[2], name, _get_sector_class(frags))


def _c2_get_name_from_offset(offset, format_output=False):
    # Deinterleave the two offsets from the single big one
    cur_idx0, cur_idx1 = util.deinterleave(offset, 32)  # No idea what length this actually is

    # Get prefixes/suffixes from the individual offsets
    p0 = _get_entry_from_offset(cur_idx0, _prefix_offsets, _prefix_offsets)
    p1 = _get_entry_from_offset(cur_idx1, _prefix_offsets, _prefix_offsets)
    s0 = _get_suffixes(p0)[cur_idx0 - _prefix_offsets[p0][0]]
    s1 = _get_suffixes(p1)[cur_idx1 - _prefix_offsets[p1][0]]

    # Done!
    output = [p0, s0, p1, s1]
    if format_output:
        output = format_sector_name(output)
    return output


def _c2_get_offset_from_name(input):
    frags = get_sector_fragments(input) if util.is_str(input) else input
    if frags is None:
        return

    try:
        # Get the current indexes within prefix runs (3037)
        cur_idx0 = _prefix_offsets[frags[0]][0] + _get_suffixes(frags[0]).index(frags[1])
        cur_idx1 = _prefix_offsets[frags[2]][0] + _get_suffixes(frags[2]).index(frags[3])
    except:
        # Either the prefix or suffix lookup failed, likely a dodgy name
        return None

    # Interleave the individual offsets into one big offset
    return util.interleave(cur_idx0, cur_idx1, 32)  # Again, length is anyone's guess


# #
# Setup functions
# #

# Cache the run offsets of all prefixes and C1 infixes
_prefix_offsets = {}
_c1_infix_offsets = {}


def _construct_offsets():
    global _prefix_offsets, _c1_infix_offsets
    cnt = 0
    for p in pgdata.cx_prefixes:
        plen = _get_prefix_run_length(p)
        _prefix_offsets[p] = (cnt, plen)
        cnt += plen
    cnt = 0
    for i in pgdata.c1_infixes_s1:
        ilen = _c1_get_infix_run_length(i)
        _c1_infix_offsets[i] = (cnt, ilen)
        cnt += ilen
    cnt = 0
    for i in pgdata.c1_infixes_s2:
        ilen = _c1_get_infix_run_length(i)
        _c1_infix_offsets[i] = (cnt, ilen)
        cnt += ilen


# #
# Initialisation
# #

_init_start = time.perf_counter()
_construct_offsets()
_init_time = time.perf_counter() - _init_start
