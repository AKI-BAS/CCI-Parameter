# -*- coding: utf-8 -*-
"""Storey codes (01, 02, K1, M2) and room numbers for location IDs.

BIM Ísland: 01 = 1. hæð, K1 = 1. kjallarahæð, K2 = 2. kjallarahæð,
M2 = millihæð ofan 2. hæðar. Room number zzz is a running number.
"""
from __future__ import unicode_literals

import re

from cci import formats


def suggest_level_codes(levels, ground_name=None):
    """Suggest a code for each level.

    levels: list of (name, elevation) in any order, elevation in any unit.
    ground_name: name of the 1. hæð. Default: the lowest level at or above
    elevation 0, else the highest level.
    Returns {name: code}. Mezzanines (M) cannot be guessed; the person
    sets those by hand.
    """
    ordered = sorted(levels, key=lambda lv: lv[1])
    if not ordered:
        return {}
    names = [lv[0] for lv in ordered]
    if ground_name in names:
        g = names.index(ground_name)
    else:
        g = None
        for i, lv in enumerate(ordered):
            if lv[1] >= -1e-6:
                g = i
                break
        if g is None:
            g = len(ordered) - 1
    codes = {}
    for i, name in enumerate(names):
        if i >= g:
            codes[name] = "%02d" % (i - g + 1)
        else:
            codes[name] = "K%d" % (g - i)
    return codes


def room_number(raw, mode="as_is", pad=3):
    """Turn a Revit room Number into zzz, or None if it can't be used.

    mode 'as_is':        '7' -> '007', '101' -> '101', '1.101' -> None
    mode 'last_segment': '2.101' -> '101', 'B1-07' -> '007'
    """
    if raw is None:
        return None
    raw = raw.strip()
    if mode == "last_segment":
        raw = re.split(r"[.\-_/ ]", raw)[-1]
    if not re.match(r"^\d+$", raw):
        return None
    if len(raw.lstrip("0") or "0") > pad:
        return None
    return ("%0" + str(pad) + "d") % int(raw)


def auto_room_numbers(rooms, pad=3):
    """Running numbers per storey for rooms that have no usable number.

    rooms: list of (key, level_code, sort_key). Numbers start at 1 per
    level and follow sort_key. Returns {key: 'zzz'}.
    """
    out = {}
    by_level = {}
    for key, level_code, sort_key in rooms:
        by_level.setdefault(level_code, []).append((sort_key, key))
    for level_code in by_level:
        for i, (_, key) in enumerate(sorted(by_level[level_code])):
            out[key] = ("%0" + str(pad) + "d") % (i + 1)
    return out


def room_location(building, level_code, number):
    """(location_id, location_at_id) or (None, issue_key)."""
    if level_code is None:
        return None, "loc.no_level_code"
    if formats.check_level_code(level_code):
        return None, "loc.bad_level_code"
    if number is None:
        return None, "loc.no_room_number"
    loc = formats.location_id(building, level_code, number)
    return loc, None
