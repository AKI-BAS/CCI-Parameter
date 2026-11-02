# -*- coding: utf-8 -*-
"""Check: what is missing, malformed or duplicated, against the project's
scope and LOD settings."""
from __future__ import unicode_literals

import codecs

from pyrevit import forms, script

from cci import checker, formats
from cci.i18n import t
from cci.revit import params, ui, util

doc = ui.doc()
ui.require_project(doc)
settings = ui.settings_or_warn(doc)
table = util.load_classes()
ruleset = util.load_rules(settings)
MAX_ROWS = 300

ALL_KEYS = list(formats.REQUIRED_PARAMS) + list(formats.OPTIONAL_PARAMS)


def records():
    out = []
    for e in util.classified_instances(doc):
        cat = util.bic_name(e)
        group, kind = util.group_and_kind(doc, e)
        etype = util.element_type(doc, e)
        rec = {"id": util.eid(e), "label": util.label(doc, e),
               "category": cat, "kind": kind, "group": group,
               "type_uid": etype.UniqueId if etype is not None else None,
               "has_point": util.point_of(e) is not None,
               "cat_name": e.Category.Name if e.Category else "",
               "exported": util.exported_to_ifc(e, etype),
               "bound": [], "values": {}}
        for key in ALL_KEYS:
            src = etype if key.endswith("_t") else e
            if src is None:
                continue
            v = util.get_key(src, key)
            if v is None:
                continue
            rec["bound"].append(key)
            rec["values"][key] = v
        out.append(rec)
    return out


recs = records()
issues = checker.check(recs, settings, table)
summary = checker.summary(issues)

out = ui.output()
out.print_md("## " + t("check.title"))
out.print_md(t("check.scope", scopes=", ".join(
    t("scope." + s) for s in settings["scopes"]) or "-"))
out.print_md(t("check.table", name=table.title or "-"))
if settings.get("table_id") and table.id and settings["table_id"] != table.id:
    out.print_md("> " + t("check.table_changed", old=settings["table_id"],
                          new=table.id))
out.print_md(t("check.summary", n=len(recs), errors=summary["error"],
               warnings=summary["warning"], infos=summary["info"]))

bound = set(n.lower() for n in params.bound_names(doc))
missing_params = [formats.PARAM[k] for k in formats.REQUIRED_PARAMS
                  if formats.PARAM[k].lower() not in bound]
src = params.source(doc)
if src in ("tool", "mixed"):
    out.print_md("> " + t("check.params_" + src))
if missing_params:
    out.print_md("**%s** %s" % (t("check.params_missing"),
                                ", ".join(missing_params)))
if not table.complete:
    out.print_md("> " + t("check.table_incomplete"))
for key, p in ruleset.problems:
    out.print_md("- " + t(key, **p))

by_key = {}
for i in issues:
    by_key.setdefault((i.severity, i.key), []).append(i)

order = {checker.ERROR: 0, checker.WARNING: 1, checker.INFO: 2}
for (sev, key), items in sorted(by_key.items(),
                                key=lambda kv: (order[kv[0][0]], kv[0][1])):
    out.print_md("### %s: %s (%d)" % (t("sev." + sev), t(key + ".h"),
                                      len(items)))
    rows = []
    for i in items[:MAX_ROWS]:
        p = dict(i.params)
        if "detail" in p:
            p["detail"] = t(p["detail"])
        rows.append([ui.link(out, i.element_id) if i.element_id else "-",
                     i.label or "-", t(key, **p)])
    out.print_table(rows, columns=[t("col.element"), t("col.name"),
                                   t("col.problem")])
    if len(items) > MAX_ROWS:
        out.print_md(t("check.more", n=len(items) - MAX_ROWS))

skipped = sum(1 for r in recs if r["exported"] is False)
if skipped:
    out.print_md(t("check.skipped_ifc", n=skipped))

out.print_md("### " + t("check.overview"))
out.print_md(t("check.overview_d"))
LANG = ui.lang()
tops = {"element": settings["topnode_elements"],
        "system": settings["topnode_elements"],
        "space": settings["topnode_spaces"]}
out.print_table(
    [[cat, code or "-", name or ("" if code else t("check.unclassified")),
      types, n] for cat, code, name, types, n in
     checker.overview(recs, table, LANG, tops)],
    columns=[t("col.category"), t("col.code"), t("col.name"),
             t("col.types"), t("col.count")])

if not issues:
    out.print_md("**" + t("check.all_ok") + "**")
elif ui.confirm("check.save_csv"):
    path = forms.save_file(file_ext="csv", default_name=t("check.csv_name"))
    if path:
        with codecs.open(path, "w", "utf-8-sig") as f:
            f.write(";".join([t("col.severity"), t("col.element"),
                              t("col.name"), t("col.problem")]) + "\r\n")
            for i in issues:
                p = dict(i.params)
                if "detail" in p:
                    p["detail"] = t(p["detail"])
                cells = [t("sev." + i.severity), str(i.element_id or ""),
                         i.label or "", t(i.key, **p)]
                f.write(";".join('"%s"' % c.replace('"', '""')
                                 for c in cells) + "\r\n")
        script.show_file_in_explorer(path)
