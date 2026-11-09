# -*- coding: utf-8 -*-
"""Locations: room numbers (CCIMultiLevelLocationID, B01.01.001) on rooms
and spaces, and the room an element sits in (CCISingleLevelLocationAtID,
+B01.01.001) on doors, windows, fixtures and equipment."""
from __future__ import unicode_literals

from Autodesk.Revit.DB import XYZ, FamilyInstance, LocationCurve, Wall

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
         "no_room_cats": {}, "multi": 0, "storey_mismatch": []}


def compute_space_codes(spaces):
    """{UniqueId: 'B01.01.001'}; problems are noted in stats."""
    out = {}
    auto = []
    for sp in spaces:
        lvl = sp.Level.Name if sp.Level else None
        lc = level_codes.get(lvl) if lvl else None
        raw = util.get(sp, "Number")
        in_number = levels.storey_of_number(raw)
        if mode == "number_storey":
            # storey from the Number itself (02-37 -> 02), not the level
            lc = in_number or lc
            num = levels.room_number(raw, "last_segment")
        elif mode == "auto":
            num = None
        else:
            num = levels.room_number(raw, mode)
        if mode == "last_segment" and in_number and lc and in_number != lc:
            stats["storey_mismatch"].append((sp, lvl, lc, raw))
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


def level_elevation(element):
    for src in (element, getattr(element, "Host", None)):
        try:
            lv = doc.GetElement(src.LevelId)
            if lv is not None:
                return lv.Elevation
        except Exception:
            continue
    return None


def level_name(element):
    """The element's level, for the report."""
    try:
        lv = doc.GetElement(element.LevelId)
        if lv is not None and getattr(lv, "Name", None):
            return lv.Name
    except Exception:
        pass
    for p in ("Level", "Schedule Level", "Base Level", "Reference Level",
              "Base Constraint"):
        v = util.get(element, p)
        if v:
            return v
    return "-"


def phases_of(element):
    """Phases to look for rooms in: the element's own phase first (rooms
    only exist in their phase), then the project's last phase."""
    out = []
    try:
        ph = doc.GetElement(element.CreatedPhaseId)
        if ph is not None:
            out.append(ph)
    except Exception:
        pass
    # rooms exist in one phase only: also look in every phase that has
    # rooms (e.g. doors in existing walls, rooms in New Construction)
    for ph in ROOM_PHASES + [last_phase()]:
        if ph is not None and not any(
                p is ph or getattr(p, "Id", 1) == getattr(ph, "Id", 2)
                for p in out):
            out.append(ph)
    return out or [None]


def _room_at(p, phase):
    try:
        return doc.GetRoomAtPoint(p, phase) if phase else \
            doc.GetRoomAtPoint(p)
    except Exception:
        return None


FLOOR_LIKE = ("OST_Floors", "OST_Roofs", "OST_Stairs", "OST_StairsRuns",
              "OST_StairsLandings", "OST_Ramps", "OST_StructuralFoundation")
WALL_HOSTED = ("OST_Windows", "OST_Doors", "OST_CurtainWallMullions",
               "OST_CurtainWallPanels")


def sample_points(element):
    """Points inside the rooms an element touches: beside a wall on both
    sides, above a floor, below a ceiling, in and around anything else."""
    try:
        bb = element.get_BoundingBox(None)
    except Exception:
        bb = None
    if bb is None:
        return []
    cat = util.bic_name(element)
    lo, hi = bb.Min, bb.Max
    if cat in FLOOR_LIKE:
        zs = [hi.Z + 1.0]
    elif cat == "OST_Ceilings":
        zs = [lo.Z - 1.0]
    else:
        zs = [lo.Z + 1.0, (lo.Z + hi.Z) / 2.0]
        lv_z = level_elevation(element)
        if lv_z is not None and lv_z + 1.0 < lo.Z:
            zs.append(lv_z + 1.0)   # high windows in rooms set low
        if cat in WALL_HOSTED:
            zs.append(lo.Z - 2.0)   # roof windows: the room is below
    pts = []
    loc = element.Location
    if isinstance(element, Wall) and isinstance(loc, LocationCurve):
        curve = loc.Curve
        side = (getattr(element, "Width", 0.0) or 0.0) / 2.0 + 1.0
        for i in range(5):
            prm = 0.1 + 0.2 * i
            try:
                pt = curve.Evaluate(prm, True)
                d = curve.ComputeDerivatives(prm, True).BasisX.Normalize()
            except Exception:
                continue
            n = XYZ(-d.Y, d.X, 0)
            for s in (1.0, -1.0):
                for z in zs:
                    pts.append(XYZ(pt.X + n.X * side * s,
                                   pt.Y + n.Y * side * s, z))
        return pts
    grow = 1.5 if cat in WALL_HOSTED else 0.0
    for i in range(4):
        for j in range(4):
            x = lo.X - grow + (hi.X - lo.X + 2 * grow) * (0.125 + 0.25 * i)
            y = lo.Y - grow + (hi.Y - lo.Y + 2 * grow) * (0.125 + 0.25 * j)
            for z in zs:
                pts.append(XYZ(x, y, z))
    return pts


def lowest_room_location(element, phases):
    """Location of the room on the lowest storey the element touches."""
    cands = []
    seen = set()
    for p in sample_points(element):
        for ph in phases:
            room = _room_at(p, ph)
            uid = getattr(room, "UniqueId", None) if room else None
            if not uid or uid in seen:
                continue
            seen.add(uid)
            try:
                elev = room.Level.Elevation if room.Level else 0.0
            except Exception:
                elev = 0.0
            cands.append((elev, codes.get(uid)))
    return levels.lowest_room(cands)


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


def _room_phases():
    out = []
    for sp in spaces:
        try:
            ph = doc.GetElement(sp.CreatedPhaseId)
        except Exception:
            ph = None
        if ph is not None and not any(
                p is ph or getattr(p, "Id", 1) == getattr(ph, "Id", 2)
                for p in out):
            out.append(ph)
    return out


ROOM_PHASES = _room_phases()

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
            util.set_key(sp, "ml_location_id", loc)
            stats["rooms"] += 1
    if write_elements:
        lowest = settings.get("multi_room", "lowest") == "lowest"
        for e in others:
            if not util.has_key(e, "location_at_id"):
                continue
            phases = phases_of(e)
            loc = None
            single = False
            for ph in phases:
                room = room_of(e, ph)
                if room is False:
                    break
                single = True
                uid = getattr(room, "UniqueId", None) if room else None
                loc = codes.get(uid) if uid else None
                if loc:
                    break
            if not loc and lowest:
                # several rooms (walls, floors, pipes) or none found at its
                # point (exterior windows, mullions): the room on the
                # lowest storey it touches
                loc = lowest_room_location(e, phases)
                if loc and not single:
                    stats["multi"] += 1
            if not loc and not single:
                stats["not_point"] += 1
                continue
            if not loc:
                stats["no_room"] += 1
                key = (e.Category.Name if e.Category else "?",
                       level_name(e))
                stats["no_room_cats"].setdefault(key, []).append(e)
                continue
            util.set_key(e, "location_at_id", "+" + loc)
            stats["elements"] += 1

out = ui.output()
out.print_md("## " + t("loc.title"))
out.print_md(t("loc.done", rooms=stats["rooms"],
               elements=stats["elements"]))
if stats["no_room"]:
    out.print_md(t("loc.no_room", n=stats["no_room"]))
    out.print_md(t("loc.no_room_why"))
    rows = sorted(stats["no_room_cats"].items(), key=lambda kv: -len(kv[1]))
    out.print_table([[c, lv, len(els),
                      " ".join(ui.link(out, util.eid(e)) for e in els[:3])]
                     for (c, lv), els in rows],
                    columns=[t("col.category"), t("col.level"),
                             t("col.count"), t("loc.col_examples")])
if stats["multi"]:
    out.print_md(t("loc.multi", n=stats["multi"]))
if stats["not_point"]:
    out.print_md(t("loc.not_point", n=stats["not_point"]))
if stats["not_bound"]:
    out.print_md(t("loc.not_bound", n=stats["not_bound"]))
if stats["storey_mismatch"]:
    out.print_md("### " + t("loc.storey_mismatch",
                            n=len(stats["storey_mismatch"])))
    out.print_md(t("loc.storey_mismatch_d"))
    groups_ = {}
    for sp, lvl, lc, raw in stats["storey_mismatch"]:
        key = (lvl or "-", lc, levels.storey_of_number(raw))
        groups_.setdefault(key, []).append(raw)
    out.print_table([[lvl, lc, s, len(nums), ", ".join(sorted(nums)[:4])]
                     for (lvl, lc, s), nums in sorted(groups_.items())],
                    columns=[t("col.level"), t("loc.col_code"),
                             t("loc.col_in_number"), t("col.count"),
                             t("loc.col_examples")])
if stats["bad_rooms"]:
    if stats["try_last"]:
        out.print_md("> **" + t("loc.hint_last_segment",
                                n=stats["try_last"]) + "**")
    out.print_md("### " + t("loc.bad_rooms", n=len(stats["bad_rooms"])))
    rows = [[ui.link(out, util.eid(sp)), lvl or "-", raw or "-",
             t(problem)] for sp, problem, lvl, raw in stats["bad_rooms"]]
    out.print_table(rows, columns=[t("col.element"), t("col.level"),
                                   t("col.number"), t("col.problem")])
