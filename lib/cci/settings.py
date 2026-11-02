# -*- coding: utf-8 -*-
"""Per-project settings (stored in the Revit project)."""
from __future__ import unicode_literals

import copy

from cci import formats, groups

DEFAULTS = {
    "version": 1,
    # Scope from page 1 of CCI leiðbeiningar v2.
    "scopes": ["coordination"],
    "building": 1,
    "ground_level": None,
    "levels": {},                  # Revit level name -> 01 / K1 / M2
    "room_number_mode": "as_is",   # as_is | last_segment | auto
    "door_room": "to",             # doors/windows: to-room or from-room first
    "lod_default": 300,
    "lod": {},                     # group id -> 200/300/325/400
    "type_pad": 3,                 # %QQC001
    "single_pad": 3,               # #QQC001
    "ml_number": "type",           # §B.AD.QQC001: type number or per element
    "topnode_elements": "L",
    "topnode_spaces": "B",
    "write_topnode": True,
    "write_classification": True,  # CCIClassification, used by IFC export
    "classification_desc": True,   # AD:Wall construction vs AD
    "copy_to_instance": True,      # copy type values onto instances
    "table_id": None,              # CCI table used when last classified
    "ifc": {
        "name": "CCI Classification",
        "source": "Molio",
        "edition": "R4",
        "edition_date": "2023-01-26",
        "location": "https://ikt.molio.dk/tools/p150",
        "field": "CCIClassification",
    },
}


def merged(stored):
    """Defaults overlaid with what is stored in the project."""
    out = copy.deepcopy(DEFAULTS)
    for key, value in (stored or {}).items():
        if key == "ifc" and isinstance(value, dict):
            out["ifc"].update(value)
        elif key in out:
            out[key] = value
    return out


def lod_for(settings, group):
    if group is None:
        return None
    return int(settings["lod"].get(group, settings["lod_default"]))


def validate(settings):
    """List of (issue_key, params)."""
    issues = []
    try:
        b = int(settings["building"])
        if b < 0 or b > 99:
            raise ValueError
    except (ValueError, TypeError):
        issues.append(("set.building", {"value": settings["building"]}))
    for name, code in sorted(settings["levels"].items()):
        if code and formats.check_level_code(code):
            issues.append(("fmt.level_code", {"value": code, "name": name}))
    for scope in settings["scopes"]:
        if scope not in groups.SCOPES:
            issues.append(("set.scope", {"value": scope}))
    for gid, lod in settings["lod"].items():
        if int(lod) not in groups.LODS:
            issues.append(("set.lod", {"value": lod, "name": gid}))
    if int(settings["lod_default"]) not in groups.LODS:
        issues.append(("set.lod", {"value": settings["lod_default"],
                                   "name": "*"}))
    for key in ("topnode_elements", "topnode_spaces"):
        if settings[key] not in formats.TOPNODES:
            issues.append(("fmt.topnode", {"value": settings[key]}))
    for key in ("type_pad", "single_pad"):
        if int(settings[key]) not in (1, 2, 3, 4):
            issues.append(("set.pad", {"value": settings[key]}))
    if settings["room_number_mode"] not in ("as_is", "last_segment", "auto"):
        issues.append(("set.room_mode", {"value":
                                         settings["room_number_mode"]}))
    return issues
