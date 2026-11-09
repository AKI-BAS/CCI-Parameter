# -*- coding: utf-8 -*-
"""Locations: room numbers (CCIMultiLevelLocationID, B01.01.001) on rooms
and spaces, and the room an element sits in (CCISingleLevelLocationAtID,
+B01.01.001) on doors, windows, fixtures and equipment."""
from __future__ import unicode_literals

from Autodesk.Revit.DB import XYZ, FamilyInstance

from cci import formats, groups, levels
from cci.i18n import t
from cci.revit import params, ui, util

doc = ui.doc()
ui.require_project(doc)
settings = ui.settings_or_warn(doc)
scopes = settings["scopes"]
write_elements = "location_id" in scopes
# room numbers are part of Operations; with Location ID they're written
# too, since +B01.01.003 on an element refers to the room's number
write_rooms = "operations" in scopes or write_elements
if not (write_rooms or write_elements):
    ui.alert("loc.nothing_in_scope", exit=True)

level_codes = settings["levels"]
building = settings["building"]
mode = settings["room_number_mode"]
stats = {"rooms": 0, "elements": 0, "no_room": 0, "not_point": 0,
         "bad_rooms": [], "not_bound": 0, "try_last": 0,
         "no_room_cats": {}}


def compute_space_codes(spaces):
    """{UniqueId: 'B01.01.001'}; problems are noted in stats."""
    out = {}
    auto = []
    for sp in spaces:
        lvl = sp.Level.Name if sp.Level else None
        lc = level_codes.get(lvl) if lvl else None
        raw = util.get(sp, "Number")
        num = None if mode == "auto" else levels.room_number(raw, mode)
        if mode == "auto":
            auto.append((sp.UniqueId, lc, (raw or "", util.eid(sp))))
        loc, problem = levels.room_location(building, lc, num) \
            if mode != "auto" else (None, None)
        if problem == "loc.no_room_number" and mode == "as_is" and \
                levels.room_number(raw, "last_segment"):
            # e.g. "01-03": the storey is already in the Number
            problem = "loc.try_last_segment"
            stats["try_last"] += 1
        if problem:
            stats["bad_rooms"].append((sp, problem, lvl, raw))
        elif loc:
            out[sp.UniqueId] = loc
    if auto:
        # keep numbers rooms already got on an earlier run
        existing = {}
        for sp in spaces:
            lvl = sp.Level.Name if sp.Level else None
            parsed = formats.parse_location(util.get_key(sp, "ml_location_id"))
            if parsed and parsed[1] == level_codes.get(lvl) and \
                    int(parsed[0]) == int(building or 0):
                existing[sp.UniqueId] = parsed[2]
        nums = levels.auto_room_numbers(auto, existing=existing)
        for sp in spaces:
            if sp.UniqueId not in nums:
                continue
            lvl = sp.Level.Name if sp.Level else None
            lc = level_codes.get(lvl) if lvl else None
            loc, problem = levels.room_location(building, lc,
                                                nums[sp.UniqueId])
            if problem:
                stats["bad_rooms"].append((sp, problem, lvl,
                                           util.get(sp, "Number")))
            else:
                out[sp.UniqueId] = loc
    return out


def last_phase():
    phases = doc.Phases
    return phases[phases.Size - 1] if phases.Size else None


def _room_prop(element, name, phase):
    """FamilyInstance.Room/Space/ToRoom/FromRoom at a phase.

    In IronPython these are indexed properties: element.Room gives an
    'indexer' object, not the room, so call get_Room(phase) instead.
    Returns a room/space or None."""
    value = None
    try:
        if phase is not None:
            value = getattr(element, "get_" + name)(phase)
        else:
            value = getattr(element, name)
    except Exception:
        return None
    return value if getattr(value, "UniqueId", None) else None


def room_of(element, phase):
    if isinstance(element, FamilyInstance):
        cat = util.bic_name(element)
        if cat in ("OST_Doors", "OST_Windows"):
            first = _room_prop(element, "ToRoom", phase)
            second = _room_prop(element, "FromRoom", phase)
            if settings["door_room"] == "from":
                first, second = second, first
            return first or second
        for name in ("Room", "Space"):
            room = _room_prop(element, name, phase)
            if room is not None:
                return room
    pt = util.point_of(element)
    if pt is None:
        return False   # walls, floors... no single room
    # a point exactly on the floor is on the room's lower boundary, and
    # ceiling lights sit at or above the room's top: try a little above,
    # the point itself, then below (Revit units are feet: 1 ft = 0.3 m)
    for p in (pt + XYZ(0, 0, 1.0), pt, pt + XYZ(0, 0, -2.0)):
        room = doc.GetRoomAtPoint(p, phase) if phase else \
            doc.GetRoomAtPoint(p)
        if room is not None:
            return room
    return None


all_elems = util.classified_instances(doc)
spaces = [e for e in all_elems
          if util.bic_name(e) in ("OST_Rooms", "OST_MEPSpaces")]
others = [e for e in all_elems if groups.kind_of(util.bic_name(e)) != "space"]

if spaces and not any(level_codes.values()):
    ui.alert("loc.no_level_codes", exit=True)

codes = compute_space_codes(spaces)

with ui.Tx(doc, "tx.locations"):
    params.allow_vary_in_groups(doc)    # or Revit ungroups group copies
    if write_rooms:
        for sp in spaces:
            loc = codes.get(sp.UniqueId)
            if not loc:
                continue
            if not util.has_key(sp, "ml_location_id"):
                stats["not_bound"] += 1
                continue
            if util.set_key(sp, "ml_location_id", loc):
                stats["rooms"] += 1
    if write_elements:
        phase = last_phase()
        for e in others:
            if not util.has_key(e, "location_at_id"):
                continue
            room = room_of(e, phase)
            if room is False:
                stats["not_point"] += 1
                continue
            uid = getattr(room, "UniqueId", None) if room else None
            loc = codes.get(uid) if uid else None
            if not loc:
                stats["no_room"] += 1
                cat = e.Category.Name if e.Category else "?"
                stats["no_room_cats"][cat] = \
                    stats["no_room_cats"].get(cat, 0) + 1
                continue
            if util.set_key(e, "location_at_id", "+" + loc):
                stats["elements"] += 1

out = ui.output()
out.print_md("## " + t("loc.title"))
out.print_md(t("loc.done", rooms=stats["rooms"],
               elements=stats["elements"]))
if stats["no_room"]:
    out.print_md(t("loc.no_room", n=stats["no_room"]))
    out.print_md(t("loc.no_room_why"))
    out.print_table(sorted(([c, n] for c, n in
                            stats["no_room_cats"].items()),
                           key=lambda r: -r[1]),
                    columns=[t("col.category"), t("col.count")])
if stats["not_point"]:
    out.print_md(t("loc.not_point", n=stats["not_point"]))
if stats["not_bound"]:
    out.print_md(t("loc.not_bound", n=stats["not_bound"]))
if stats["bad_rooms"]:
    if stats["try_last"]:
        out.print_md("> **" + t("loc.hint_last_segment",
                                n=stats["try_last"]) + "**")
    out.print_md("### " + t("loc.bad_rooms", n=len(stats["bad_rooms"])))
    rows = [[ui.link(out, util.eid(sp)), lvl or "-", raw or "-",
             t(problem)] for sp, problem, lvl, raw in stats["bad_rooms"]]
    out.print_table(rows, columns=[t("col.element"), t("col.level"),
                                   t("col.number"), t("col.problem")])
