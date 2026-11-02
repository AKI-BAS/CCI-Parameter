# -*- coding: utf-8 -*-
"""Locations: room numbers (CCIMultiLevelLocationID, B01.01.001) on rooms
and spaces, and the room an element sits in (CCISingleLevelLocationAtID,
+B01.01.001) on doors, windows, fixtures and equipment."""
from __future__ import unicode_literals

from Autodesk.Revit.DB import FamilyInstance

from cci import groups, levels
from cci.i18n import t
from cci.revit import ui, util

doc = ui.doc()
ui.require_project(doc)
settings = ui.settings_or_warn(doc)
scopes = settings["scopes"]
write_rooms = "operations" in scopes
write_elements = "location_id" in scopes
if not (write_rooms or write_elements):
    ui.alert("loc.nothing_in_scope", exit=True)

level_codes = settings["levels"]
building = settings["building"]
mode = settings["room_number_mode"]
stats = {"rooms": 0, "elements": 0, "no_room": 0, "not_point": 0,
         "bad_rooms": [], "not_bound": 0}


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
        if problem:
            stats["bad_rooms"].append((sp, problem, lvl, raw))
        elif loc:
            out[sp.UniqueId] = loc
    if auto:
        nums = levels.auto_room_numbers(auto)
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


def room_of(element, phase):
    if isinstance(element, FamilyInstance):
        cat = util.bic_name(element)
        if cat in ("OST_Doors", "OST_Windows"):
            if phase is not None:
                first, second = (element.get_ToRoom(phase),
                                 element.get_FromRoom(phase))
            else:
                first, second = element.ToRoom, element.FromRoom
            if settings["door_room"] == "from":
                first, second = second, first
            return first or second
        try:
            room = element.Room
            if room is not None:
                return room
        except Exception:
            pass
        try:
            space = element.Space
            if space is not None:
                return space
        except Exception:
            pass
    pt = util.point_of(element)
    if pt is None:
        return False   # walls, floors... no single room
    return doc.GetRoomAtPoint(pt, phase) if phase else doc.GetRoomAtPoint(pt)


all_elems = util.classified_instances(doc)
spaces = [e for e in all_elems
          if util.bic_name(e) in ("OST_Rooms", "OST_MEPSpaces")]
others = [e for e in all_elems if groups.kind_of(util.bic_name(e)) != "space"]

if spaces and not any(level_codes.values()):
    ui.alert("loc.no_level_codes", exit=True)

codes = compute_space_codes(spaces)

with ui.Tx(doc, "tx.locations"):
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
            loc = codes.get(room.UniqueId) if room is not None else None
            if not loc:
                stats["no_room"] += 1
                continue
            if util.set_key(e, "location_at_id", "+" + loc):
                stats["elements"] += 1

out = ui.output()
out.print_md("## " + t("loc.title"))
out.print_md(t("loc.done", rooms=stats["rooms"],
               elements=stats["elements"]))
if stats["no_room"]:
    out.print_md(t("loc.no_room", n=stats["no_room"]))
if stats["not_point"]:
    out.print_md(t("loc.not_point", n=stats["not_point"]))
if stats["not_bound"]:
    out.print_md(t("loc.not_bound", n=stats["not_bound"]))
if stats["bad_rooms"]:
    out.print_md("### " + t("loc.bad_rooms", n=len(stats["bad_rooms"])))
    rows = [[ui.link(out, util.eid(sp)), lvl or "-", raw or "-",
             t(problem)] for sp, problem, lvl, raw in stats["bad_rooms"]]
    out.print_table(rows, columns=[t("col.element"), t("col.level"),
                                   t("col.number"), t("col.problem")])
