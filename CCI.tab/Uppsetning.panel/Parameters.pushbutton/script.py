# -*- coding: utf-8 -*-
"""Add the CCI parameters: from Molio's shared parameter file (C420) when
the studio has it, otherwise from CCI-tools' own file with the same names.
A project can later be moved to Molio's file without losing values."""
from __future__ import unicode_literals

import os

from pyrevit import forms, script

from cci import formats, sharedparams
from cci.i18n import t
from cci.revit import params, ui, util

doc = ui.doc()
ui.require_project(doc)
app = doc.Application
cfg = script.get_config()
store = util.store()

OPTIONS = ["molio", "tool", "export_project", "save_tool"]
labels = [t("params.opt_" + o) for o in OPTIONS]
choice = forms.CommandSwitchWindow.show(labels, message=t("params.choose"))
if not choice:
    script.exit()
mode = OPTIONS[labels.index(choice)]

if mode == "export_project":
    entries = params.project_entries(doc)
    if not entries:
        ui.alert("params.no_project_params", exit=True)
    path = forms.save_file(file_ext="txt",
                           default_name="CCI_SharedParameters_" +
                           (doc.Title or "verkefni").replace(".rvt", ""))
    if path:
        tool = sum(1 for n, g, _, _ in entries
                   if sharedparams.is_tool_guid(n, g))
        sharedparams.write_file(
            path, entries, ["# CCI parameters saved from the project "
                            "'%s' by CCI-tools." % doc.Title])
        ui.alert("params.exported_project", path=path, n=len(entries),
                 names=", ".join(n for n, _, _, _ in entries),
                 source=t("params.src_tool" if tool == len(entries)
                          else "params.src_other"))
    script.exit()

if mode == "save_tool":
    path = forms.save_file(file_ext="txt",
                           default_name=sharedparams.FILE_NAME[:-4])
    if path:
        sharedparams.write_file(path)
        ui.alert("params.saved_tool", path=path)
    script.exit()

if mode == "tool":
    if not os.path.isdir(store.user):
        os.makedirs(store.user)
    path = sharedparams.write_file(
        os.path.join(store.user, sharedparams.FILE_NAME))
else:
    last = cfg.get_option("shared_param_file", "")
    if last and os.path.exists(last) and ui.confirm("params.use_last",
                                                    path=last):
        path = last
    else:
        path = forms.pick_file(file_ext="txt", title=t("params.pick"))
    if not path:
        script.exit()
    info = sharedparams.check_file(sharedparams.read_text(path))
    if not info["found"]:
        ui.alert("params.no_cci", exit=True, path=path)
    if info["tool_file"]:
        if not ui.confirm("params.is_tool_file"):
            script.exit()
    cfg.shared_param_file = path
    script.save_config()

defs = params.read_definitions(app, path)
if defs is None:
    ui.alert("params.bad_file", exit=True, path=path)

keys = list(formats.REQUIRED_PARAMS)
keys += [k for k in formats.OPTIONAL_PARAMS
         if params.find_definition(defs, formats.PARAM[k]) is not None]

with ui.Tx(doc, "tx.params"):
    report = params.bind_all(doc, defs, keys)

moved = None
if report["other_file"] and mode == "molio":
    if ui.confirm("params.migrate_ask", n=len(report["other_file"])):
        try:
            with ui.Tx(doc, "tx.params_migrate"):
                moved = params.migrate(doc, defs, report["other_file"])
        except params.MigrationError as ex:
            # the transaction was rolled back: the project is as it was
            moved = {"moved": [], "failed": [
                ("-", t("params.migrate_rolled_back", error="%s" % ex))]}

util.use_project_names(doc)

out = ui.output()
out.print_md("## " + t("params.title"))
out.print_md(t("params.file", path=path))
if mode == "tool":
    out.print_md("> " + t("params.tool_note"))
for group in ("added", "updated", "unchanged", "other_file", "missing",
              "wrong_type", "conflict"):
    names = report[group]
    if not names:
        continue
    out.print_md("**%s** (%d)" % (t("params." + group), len(names)))
    for n in names:
        out.print_md("- `%s`" % n)
if report["missing"]:
    out.print_md(t("params.missing_help"))
if report["conflict"]:
    out.print_md(t("params.conflict_help"))
if report["other_file"] and moved is None:
    out.print_md(t("params.other_file_help"))
if moved:
    out.print_md("### " + t("params.migrated"))
    for name, n in moved["moved"]:
        out.print_md("- `%s`: %s" % (name, t("params.values", n=n)))
    for name, err in moved["failed"]:
        out.print_md("- `%s`: %s" % (name, err))
if "classification" not in keys:
    out.print_md(t("params.no_classification"))
