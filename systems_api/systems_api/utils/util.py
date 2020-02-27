import numbers
from . import vector3


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

