# -*- coding: utf-8 -*-
"""Number: CCITypeID (%QQC001), CCIMultiLevelTypeID (§B.AD.QQC001) and
CCISingleLevelID (#QQC001). Numbers are stable: an element keeps its
number for good, and numbers are never reused."""
from __future__ import unicode_literals

from pyrevit import forms

from cci import formats, groups, numbering, settings as smod
from cci.i18n import t
from cci.revit import storage, ui, util

doc = ui.doc()
ui.require_project(doc)
settings = ui.settings_or_warn(doc)
ruleset = util.load_rules(settings)
scopes = settings["scopes"]

do_type = "coordination" in scopes or "operations" in scopes
do_ml = "operations" in scopes
do_single_all = "product_id" in scopes

if not (do_type or do_ml or do_single_all or
        settings["lod"].get("openings", settings["lod_default"]) >= 400):
    ui.alert("number.nothing_in_scope", exit=True)

copy = settings["copy_to_instance"]
stats = {"type": 0, "ml": 0, "single": 0, "no_class": 0, "no_parents": 0,
         "not_bound": 0}


def run():
    registry = storage.load_registry(doc)
    # retire numbers of things that were deleted
    for s in list(registry.items):
        for uid in list(registry.items[s]):
            if doc.GetElement(uid) is None:
                del registry.items[s][uid]
    for uid in list(registry.parents):
        if doc.GetElement(uid) is None:
            del registry.parents[uid]

    by_type = {}
    for e in util.classified_instances(doc):
        if groups.kind_of(util.bic_name(e)) == "space":
            continue
        etype = util.element_type(doc, e)
        if etype is None:
            continue
        by_type.setdefault(etype.UniqueId, (etype, []))[1].append(e)

    # stable order: types by existing number then name, so first runs
    # number in a readable order
    def type_order(item):
        etype = item[1][0]
        return (util.get_key(etype, "type_id_t") or "~",
                util.bic_name(etype) or "", util.family_name(etype),
                util.type_name(etype))

    for uid, (etype, insts) in sorted(by_type.items(), key=type_order):
        code = util.get_key(etype, "class_t") or ""
        if not code or formats.check_class(code):
            stats["no_class"] += len(insts)
            continue
        type_no = None
        if do_type:
            if not util.has_key(etype, "type_id_t"):
                stats["not_bound"] += 1
            else:
                old = util.get_key(etype, "type_id_t") or ""
                type_no = registry.number_for(
                    numbering.series("type", code), uid, old)
                new = formats.type_id(code, type_no, settings["type_pad"])
                if formats.has_subtype(old, code):
                    new = old   # hand-made subtype (%QQC01.001): keep
                if util.set_key(etype, "type_id_t", new):
                    stats["type"] += 1
                for inst in insts:
                    if util.has_key(inst, "type_id"):
                        v = numbering.resolve_instance(
                            util.get_key(inst, "type_id"), old, new, copy)
                        if v is not None:
                            util.set_key(inst, "type_id", v)

        parents = registry.parents.get(uid)
        if not parents:
            res = ruleset.classify(util.facts(doc, insts[0], etype))
            if res.class_code == code and res.u and res.vv:
                parents = {"u": res.u, "vv": res.vv}

        for inst in sorted(insts, key=util.eid):
            inst_code = util.get_key(inst, "class") or code
            group, _ = util.group_and_kind(doc, inst)
            lod = smod.lod_for(settings, group)

            if do_ml and len(code) == 3 and util.has_key(inst, "ml_type_id"):
                if not parents:
                    stats["no_parents"] += 1
                else:
                    if settings["ml_number"] == "type" and type_no:
                        n = type_no
                    else:
                        series = numbering.series(
                            "ml", "%s.%s.%s" % (parents["u"], parents["vv"],
                                                code))
                        n = registry.number_for(
                            series, inst.UniqueId,
                            util.get_key(inst, "ml_type_id"))
                    value = formats.ml_type_id(parents["u"], parents["vv"],
                                               code, n, settings["type_pad"])
                    current = util.get_key(inst, "ml_type_id")
                    if formats.has_subtype(current, code):
                        value = current
                    if util.set_key(inst, "ml_type_id", value):
                        stats["ml"] += 1

            want_single = do_single_all or (group == "openings"
                                             and lod and lod >= 400)
            if want_single and not formats.check_class(inst_code):
                if not util.has_key(inst, "single_id"):
                    stats["not_bound"] += 1
                    continue
                n = registry.number_for(
                    numbering.series("single", inst_code), inst.UniqueId,
                    util.get_key(inst, "single_id"))
                value = formats.single_id(inst_code, n,
                                          settings["single_pad"])
                if util.set_key(inst, "single_id", value):
                    stats["single"] += 1

    storage.save_registry(doc, registry)


with ui.Tx(doc, "tx.number"):
    run()

lines = [t("number.done", type=stats["type"], ml=stats["ml"],
           single=stats["single"])]
if stats["no_class"]:
    lines.append(t("number.no_class", n=stats["no_class"]))
if stats["no_parents"]:
    lines.append(t("number.no_parents", n=stats["no_parents"]))
if stats["not_bound"]:
    lines.append(t("number.not_bound", n=stats["not_bound"]))
forms.alert("\n\n".join(lines), title=t("number.title"))
