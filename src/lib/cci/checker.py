# -*- coding: utf-8 -*-
"""Checks a model's CCI data against the project settings.

Works on plain records so it can be tested without Revit:

    {"id": "12345",              # element id (for links in the report)
     "type_uid": "...",          # type UniqueId, or None
     "label": "Doors: Single: 900",
     "category": "OST_Doors",
     "kind": "element",          # element | system | space
     "group": "doors",           # LOD group or None
     "bound": ["class", "class_t", ...],   # parameters present
     "values": {"class": "", "class_t": "QQC", ...}}
"""
from __future__ import unicode_literals

from cci import formats, groups, settings as settings_mod

ERROR, WARNING, INFO = "error", "warning", "info"

# logical field -> (instance param key, type param key or None)
FIELDS = {
    "class": ("class", "class_t"),
    "topnode": ("topnode", "topnode_t"),
    "type_id": ("type_id", "type_id_t"),
    "ml_type_id": ("ml_type_id", None),
    "functional_id": ("functional_id", None),
    "ml_location_id": ("ml_location_id", None),
    "single_id": ("single_id", None),
    "location_at_id": ("location_at_id", None),
    "classification": ("classification", "classification_t"),
}


class Issue(object):
    def __init__(self, severity, key, params, element_id, label):
        self.severity = severity
        self.key = key
        self.params = params
        self.element_id = element_id
        self.label = label

    def __repr__(self):
        return "Issue(%s, %s, %s)" % (self.severity, self.key,
                                      self.element_id)


def effective(record, field):
    """(value, where) - instance value wins over type value."""
    inst, typ = FIELDS[field]
    values = record.get("values") or {}
    v = values.get(inst) or ""
    if v:
        return v, "instance"
    if typ:
        v = values.get(typ) or ""
        if v:
            return v, "type"
    return "", None


def _bound(record, field):
    inst, typ = FIELDS[field]
    bound = record.get("bound") or []
    return inst in bound or (typ is not None and typ in bound)


def check(records, project_settings, class_table=None):
    s = project_settings
    issues = []

    def add(sev, key, rec, **params):
        issues.append(Issue(sev, key, params, rec.get("id"),
                            rec.get("label")))

    seen_single = {}
    seen_loc = {}
    type_ids = {}

    for rec in records:
        kind = rec.get("kind", "element")
        group = rec.get("group")
        lod = settings_mod.lod_for(s, group)
        need = groups.required_fields(kind, group, lod, s["scopes"])
        allowed = groups.PARAMS_BY_KIND[kind]
        cls_now, _ = effective(rec, "class")
        if cls_now and len(cls_now) != 3 and "ml_type_id" in need:
            # §U.VV.XXX needs a component (3 letters); systems such as
            # AD (walls) can't have one.
            need.remove("ml_type_id")
        if rec.get("has_point") is False and "location_at_id" in need:
            # walls, floors, ducts... span several rooms
            need.remove("location_at_id")

        # required fields
        for f in need:
            if not _bound(rec, f):
                add(ERROR, "chk.not_bound", rec,
                    param=formats.PARAM[FIELDS[f][0]])
                continue
            value, _ = effective(rec, f)
            if not value:
                add(ERROR, "chk.missing", rec,
                    param=formats.PARAM[FIELDS[f][0]])

        values = rec.get("values") or {}
        # formats, and values where they don't belong
        for pkey, value in values.items():
            if not value:
                continue
            if pkey not in allowed:
                add(WARNING, "chk.not_applicable", rec,
                    param=formats.PARAM.get(pkey, pkey))
            check_fn = formats.VALIDATORS.get(pkey)
            err = check_fn(value) if check_fn else None
            if err:
                add(ERROR, "chk.format", rec,
                    param=formats.PARAM.get(pkey, pkey), value=value,
                    detail=err)

        # instance overrides type
        for f, (inst, typ) in FIELDS.items():
            if typ and values.get(inst) and values.get(typ) \
                    and values[inst] != values[typ]:
                add(INFO, "chk.override", rec,
                    param=formats.PARAM[inst], value=values[inst],
                    type_value=values[typ])

        # class known?
        code, _ = effective(rec, "class")
        if code and not formats.check_class(code) and class_table:
            tn_now, _ = effective(rec, "topnode")
            if not tn_now:
                tn_now = "[%s]" % (s["topnode_spaces"] if kind == "space"
                                   else s["topnode_elements"])
            if not class_table.known(code, tn_now):
                if class_table.complete:
                    add(ERROR, "chk.unknown_class", rec, value=code)
                else:
                    add(INFO, "chk.unverified_class", rec, value=code)

        # IDs must carry the same class as CCIClassCode
        if code:
            for f in ("type_id", "single_id", "ml_type_id"):
                v, _ = effective(rec, f)
                inner = formats.class_of_id(v)
                if v and inner and inner != code:
                    add(ERROR, "chk.id_class_mismatch", rec,
                        param=formats.PARAM[FIELDS[f][0]], value=v,
                        code=code)

        # CCIClassification should agree with topnode + class
        cls_val, _ = effective(rec, "classification")
        if cls_val and code:
            tn, _ = effective(rec, "topnode")
            expected = (tn if s["classification_with_topnode"] else "") + code
            if cls_val != expected:
                add(WARNING, "chk.classification_mismatch", rec,
                    value=cls_val, expected=expected)

        # collect for duplicate checks
        v, _ = effective(rec, "single_id")
        if v:
            seen_single.setdefault(v, []).append(rec)
        v, _ = effective(rec, "ml_location_id")
        if v and kind == "space":
            seen_loc.setdefault(v, []).append(rec)
        v, where = effective(rec, "type_id")
        if v and where == "type" and rec.get("type_uid"):
            type_ids.setdefault(v, set()).add(rec["type_uid"])

    for value, recs in sorted(seen_single.items()):
        if len(recs) > 1:
            for rec in recs:
                add(ERROR, "chk.duplicate", rec, param=formats.PARAM[
                    "single_id"], value=value, count=len(recs))
    for value, recs in sorted(seen_loc.items()):
        if len(recs) > 1:
            for rec in recs:
                add(ERROR, "chk.duplicate", rec, param=formats.PARAM[
                    "ml_location_id"], value=value, count=len(recs))
    for value, uids in sorted(type_ids.items()):
        if len(uids) > 1:
            issues.append(Issue(ERROR, "chk.duplicate_type_id",
                                {"value": value, "count": len(uids)},
                                None, None))
    return issues


def summary(issues):
    out = {ERROR: 0, WARNING: 0, INFO: 0}
    for i in issues:
        out[i.severity] += 1
    return out
