# Procedural Generated system comprehension
# Based in part on pgdata.py from EDTS.

import collections
import re
from . import pgdata

pg_system_regex_str = r"(?P<sector>[\w\s'.()/-]+) (?P<l1>[A-Za-z])(?P<l2>[A-Za-z])-(?P<l3>[A-Za-z]) (?P<mcode>[A-Za-z])(?:(?P<n1>\d+)-)?(?P<n2>\d+)"
pg_system_search_regex = re.compile(pg_system_regex_str)
pg_system_regex = re.compile(r"^" + pg_system_regex_str + r"$")

# Hopefully-complete list of valid name fragments / phonemes
cx_raw_fragments = [
  "Th", "Eo", "Oo", "Eu", "Tr", "Sly", "Dry", "Ou",
  "Tz", "Phl", "Ae", "Sch", "Hyp", "Syst", "Ai", "Kyl",
  "Phr", "Eae", "Ph", "Fl", "Ao", "Scr", "Shr", "Fly",
  "Pl", "Fr", "Au", "Pry", "Pr", "Hyph", "Py", "Chr",
  "Phyl", "Tyr", "Bl", "Cry", "Gl", "Br", "Gr", "By",
  "Aae", "Myc", "Gyr", "Ly", "Myl", "Lych", "Myn", "Ch",
  "Myr", "Cl", "Rh", "Wh", "Pyr", "Cr", "Syn", "Str",
  "Syr", "Cy", "Wr", "Hy", "My", "Sty", "Sc", "Sph",
  "Spl", "A", "Sh", "B", "C", "D", "Sk", "Io",
  "Dr", "E", "Sl", "F", "Sm", "G", "H", "I",
  "Sp", "J", "Sq", "K", "L", "Pyth", "M", "St",
  "N", "O", "Ny", "Lyr", "P", "Sw", "Thr", "Lys",
  "Q", "R", "S", "T", "Ea", "U", "V", "W",
  "Schr", "X", "Ee", "Y", "Z", "Ei", "Oe",

  "ll", "ss", "b", "c", "d", "f", "dg", "g", "ng", "h", "j", "k", "l", "m", "n",
  "mb", "p", "q", "gn", "th", "r", "s", "t", "ch", "tch", "v", "w", "wh",
  "ck", "x", "y", "z", "ph", "sh", "ct", "wr", "o", "ai", "a", "oi", "ea",
  "ie", "u", "e", "ee", "oo", "ue", "i", "oa", "au", "ae", "oe", "scs",
  "wsy", "vsky", "sms", "dst", "rb", "nts", "rd", "rld", "lls", "rgh",
  "rg", "hm", "hn", "rk", "rl", "rm", "cs", "wyg", "rn", "hs", "rbs", "rp",
  "tts", "wn", "ms", "rr", "mt", "rs", "cy", "rt", "ws", "lch", "my", "ry",
  "nks", "nd", "sc", "nk", "sk", "nn", "ds", "sm", "sp", "ns", "nt", "dy",
  "st", "rrs", "xt", "nz", "sy", "xy", "rsch", "rphs", "sts", "sys", "sty",
  "tl", "tls", "rds", "nch", "rns", "ts", "wls", "rnt", "tt", "rdy", "rst",
  "pps", "tz", "sks", "ppy", "ff", "sps", "kh", "sky", "lts", "wnst", "rth",
  "ths", "fs", "pp", "ft", "ks", "pr", "ps", "pt", "fy", "rts", "ky",
  "rshch", "mly", "py", "bb", "nds", "wry", "zz", "nns", "ld", "lf",
  "gh", "lks", "sly", "lk", "rph", "ln", "bs", "rsts", "gs", "ls", "vvy",
  "lt", "rks", "qs", "rps", "gy", "wns", "lz", "nth", "phs", "io", "oea",
  "aa", "ua", "eia", "ooe", "iae", "oae", "ou", "uae", "ao", "eae", "aea",
  "ia", "eou", "aei", "uia", "aae", "eau" ]

# Sort fragments by length to ensure we check the longest ones first
cx_fragments = sorted(cx_raw_fragments, key=len, reverse=True)

# Order here is relevant, keep it
cx_prefixes = cx_raw_fragments[0:111]

#
# Sequences used in runs
#

# Vowel-ish infixes
c1_infixes_s1 = [
  "o", "ai", "a", "oi", "ea", "ie", "u", "e",
  "ee", "oo", "ue", "i", "oa", "au", "ae", "oe"
]

# Consonant-ish infixes
c1_infixes_s2 = [
  "ll", "ss", "b", "c", "d", "f", "dg", "g",
  "ng", "h", "j", "k", "l", "m", "n", "mb",
  "p", "q", "gn", "th", "r", "s", "t", "ch",
  "tch", "v", "w", "wh", "ck", "x", "y", "z",
  "ph", "sh", "ct", "wr"
]

c1_infixes = [
  [],
  c1_infixes_s1,
  c1_infixes_s2
]


# Sequence 1
cx_suffixes_s1 = [
  "oe",  "io",  "oea", "oi",  "aa",  "ua", "eia", "ae",
  "ooe", "oo",  "a",   "ue",  "ai",  "e",  "iae", "oae",
  "ou",  "uae", "i",   "ao",  "au",  "o",  "eae", "u",
  "aea", "ia",  "ie",  "eou", "aei", "ea", "uia", "oa",
  "aae", "eau", "ee"
]

# Sequence 2
c1_suffixes_s2 = [
  "b", "scs", "wsy", "c", "d", "vsky", "f", "sms",
  "dst", "g", "rb", "h", "nts", "ch", "rd", "rld",
  "k", "lls", "ck", "rgh", "l", "rg", "m", "n",
  # Formerly sequence 4/5...
  "hm", "p", "hn", "rk", "q", "rl", "r", "rm",
  "s", "cs", "wyg", "rn", "ct", "t", "hs", "rbs",
  "rp", "tts", "v", "wn", "ms", "w", "rr", "mt",
  "x", "rs", "cy", "y", "rt", "z", "ws", "lch", # "y" is speculation
  "my", "ry", "nks", "nd", "sc", "ng", "sh", "nk",
  "sk", "nn", "ds", "sm", "sp", "ns", "nt", "dy",
  "ss", "st", "rrs", "xt", "nz", "sy", "xy", "rsch",
  "rphs", "sts", "sys", "sty", "th", "tl", "tls", "rds",
  "nch", "rns", "ts", "wls", "rnt", "tt", "rdy", "rst",
  "pps", "tz", "tch", "sks", "ppy", "ff", "sps", "kh",
  "sky", "ph", "lts", "wnst", "rth", "ths", "fs", "pp",
  "ft", "ks", "pr", "ps", "pt", "fy", "rts", "ky",
  "rshch", "mly", "py", "bb", "nds", "wry", "zz", "nns",
  "ld", "lf", "gh", "lks", "sly", "lk", "ll", "rph",
  "ln", "bs", "rsts", "gs", "ls", "vvy", "lt", "rks",
  "qs", "rps", "gy", "wns", "lz", "nth", "phs"
]

# Class 2 appears to use a subset of sequence 2
c2_suffixes_s2 = c1_suffixes_s2[0:len(cx_suffixes_s1)]


c1_suffixes = [
  [],
  cx_suffixes_s1,
  c1_suffixes_s2
]

c2_suffixes = [
  [],
  cx_suffixes_s1,
  c2_suffixes_s2
]

# These prefixes use the specified index into the c2_suffixes list
c2_prefix_suffix_override_map = {
  "Eo":  2,  "Oo": 2, "Eu": 2,
  "Ou":  2,  "Ae": 2, "Ai": 2,
  "Eae": 2,  "Ao": 2, "Au": 2,
  "Aae": 2
}

# These prefixes use the specified index into the c1_infixes list
c1_prefix_infix_override_map = {
  "Eo": 2, "Oo":  2, "Eu":  2, "Ou": 2,
  "Ae": 2, "Ai":  2, "Eae": 2, "Ao": 2,
  "Au": 2, "Aae": 2, "A":   2, "Io": 2,
  "E":  2, "I":   2, "O":   2, "Ea": 2,
  "U":  2, "Ee":  2, "Ei":  2, "Oe": 2
}


# The default run length for most prefixes
cx_prefix_length_default = 35
# Some prefixes use short run lengths; specify them here
cx_prefix_length_overrides = {
   'Eu': 31,  'Sly':  4,   'Tz':  1,  'Phl': 13,
   'Ae': 12,  'Hyp': 25,  'Kyl': 30,  'Phr': 10,
  'Eae':  4,   'Ao':  5,  'Scr': 24,  'Shr': 11,
  'Fly': 20,  'Pry':  3, 'Hyph': 14,   'Py': 12,
 'Phyl':  8,  'Tyr': 25,  'Cry':  5,  'Aae':  5,
  'Myc':  2,  'Gyr': 10,  'Myl': 12, 'Lych':  3,
  'Myn': 10,  'Myr':  4,   'Rh': 15,   'Wr': 31,
  'Sty':  4,  'Spl': 16,   'Sk': 27,   'Sq':  7,
 'Pyth':  1,  'Lyr': 10,   'Sw': 24,  'Thr': 32,
  'Lys': 10, 'Schr':  3,    'Z': 34,
}
# Get the total length of one run over all prefixes
cx_prefix_total_run_length = sum([cx_prefix_length_overrides.get(p, cx_prefix_length_default) for p in cx_prefixes])

# Default infix run lengths
c1_infix_s1_length_default = len(c1_suffixes_s2)
c1_infix_s2_length_default = len(cx_suffixes_s1)
# Some infixes use short runs too
c1_infix_length_overrides = {
  # Sequence 1
 'oi':  88,  'ue': 147,  'oa':  57,
 'au': 119,  'ae':  12,  'oe':  39,
  # Sequence 2
 'dg':  31, 'tch':  20,  'wr':  31,
}
# Total lengths of runs over all infixes, for each sequence
c1_infix_s1_total_run_length = sum([c1_infix_length_overrides.get(p, c1_infix_s1_length_default) for p in c1_infixes_s1])
c1_infix_s2_total_run_length = sum([c1_infix_length_overrides.get(p, c1_infix_s2_length_default) for p in c1_infixes_s2])

