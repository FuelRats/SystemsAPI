import numbers
from . import vector3
import pyramid.httpexceptions as exc


def check_params(paramlist, request):
    """
    Checks whether a request contains the required parameters for an endpoint, returns a HTTPException
    if it doesn't.
    :param paramlist: A list of parameters to check that /at least one/ of is present.
    :param request: The Pyramid request object
    :return: True if param(s) are set, or a HTTPException.
    """
    for param in paramlist:
        if param in request['params']:
            return True
        else:
            continue
    return exc.HTTPBadRequest()


def get_as_position(v):
    if v is None:
        return None
    # If it's already a vector, all is OK
    if isinstance(v, vector3.Vector3):
        return v
    if hasattr(v, "position"):
        return v.position
    if hasattr(v, "centre"):
        return v.centre
    if hasattr(v, "system"):
        return get_as_position(v.system)
    try:
        if len(v) == 3 and all([isinstance(i, numbers.Number) for i in v]):
            return vector3.Vector3(v[0], v[1], v[2])
    except:
        pass
    return None


def is_str(s):
    return isinstance(s, str)


# 32-bit hashing algorithm found at http://papa.bretmulvey.com/post/124027987928/hash-functions
# Seemingly originally by Bob Jenkins <bob_jenkins-at-burtleburtle.net> in the 1990s
def jenkins32(key):
    key += (key << 12)
    key &= 0xFFFFFFFF
    key ^= (key >> 22)
    key += (key << 4)
    key &= 0xFFFFFFFF
    key ^= (key >> 9)
    key += (key << 10)
    key &= 0xFFFFFFFF
    key ^= (key >> 2)
    key += (key << 7)
    key &= 0xFFFFFFFF
    key ^= (key >> 12)
    return key


def checkpermitname(system, permsystems, perms):
    if system not in perms:
        return None
    if permsystems.get(system).permit_name is not None:
        return permsystems.get(system).permit_name
    return None


def resultstocandidates(rows, has_similarity, permsystems, perm_systems):
    candidates = []
    if has_similarity:
        for candidate in rows:
            candidates.append({'name': candidate[0].name, 'distance': candidate[1],
                               'id64': candidate[0].id64,
                               'permit_required': True if candidate[0].id64 in perm_systems else False,
                               'permit_name': checkpermitname(candidate[0].id64, permsystems, perm_systems)
                               })
    else:
        for candidate in rows:
            candidates.append({'name': candidate.name, 'similarity': 1,
                               'id64': candidate.id64,
                               'permit_required': True if candidate.id64 in perm_systems else False,
                               'permit_name': checkpermitname(candidate.id64, permsystems, perm_systems)
                               })
