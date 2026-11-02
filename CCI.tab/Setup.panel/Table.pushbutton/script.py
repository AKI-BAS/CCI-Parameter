# -*- coding: utf-8 -*-
"""CCI table: see which table is in use, load a newer one from a link or
files, switch version, and export/import the Icelandic names."""
from __future__ import unicode_literals

import codecs
import os

from pyrevit import forms, script

from cci import importer
from cci.i18n import t
from cci.revit import download, ui, util

doc = ui.doc()
store = util.store()
LANG = ui.lang()

OPTIONS = ["info", "link", "files", "switch", "export", "import", "folder"]


def show_import_log(out, log):
    sheets = [p for k, p in log if k == "imp.sheet"]
    conflicts = [p for k, p in log if k == "imp.conflict"]
    for p in sheets:
        out.print_md("- " + t("imp.sheet", **p))
    if conflicts:
        out.print_md("**" + t("table.conflicts", n=len(conflicts)) + "**")
        out.print_table([[p["code"], p["field"], p["kept"], p["other"]]
                         for p in conflicts],
                        columns=[t("col.code"), t("col.field"),
                                 t("col.kept"), t("col.other")])


def info():
    table = store.load_table()
    cfg = store.config()
    out = ui.output()
    out.print_md("## " + t("table.title"))
    if not table.id:
        out.print_md(t("table.none"))
        return
    counts = importer.counts(table.data)
    out.print_md(t("table.active", name=table.title, id=table.id))
    out.print_md(t("table.counts", l=counts["L"], s=counts["S"],
                   e=counts["E"], d=counts.get("D", 0)))
    done, total = table.coverage()
    out.print_md(t("table.names", done=done, total=total))
    out.print_md(t("table.folder", path=store.user))
    if cfg.get("table_link"):
        out.print_md(t("table.link", link=cfg["table_link"]))
    hist = cfg.get("history") or []
    if hist:
        out.print_md("### " + t("table.history"))
        out.print_table([[h.get("id"), h.get("imported", ""),
                          h.get("source", "")] for h in hist],
                        columns=["id", t("col.date"), t("col.source")])
    if doc is not None and not doc.IsFamilyDocument:
        used = util.used_codes(doc)
        missing = sorted((tn, c, n) for (tn, c), n in used.items()
                         if not table.known(c, "[%s]" % tn))
        if missing:
            out.print_md("### " + t("table.model_unknown", n=len(missing)))
            out.print_table([["[%s]%s" % (tn, c), n] for tn, c, n in missing],
                            columns=[t("col.code"), t("col.count")])


def load_and_confirm(paths, source):
    log = []
    try:
        new = importer.read_any(paths, log)
    except importer.ImportError_ as ex:
        ui.alert(ex.key, **ex.params)
        return
    except Exception as ex:
        ui.alert("table.read_failed", error="%s" % ex)
        return
    old = store.load_table_data()
    d = importer.diff(old, new)
    counts = importer.counts(new)
    out = ui.output()
    out.print_md("## " + t("table.new_title", name=new.get("name") or
                           new["id"]))
    out.print_md(t("table.counts", l=counts["L"], s=counts["S"],
                   e=counts["E"], d=counts.get("D", 0)))
    show_import_log(out, log)
    out.print_md(t("table.diff", added=len(d["added"]),
                   removed=len(d["removed"]), renamed=len(d["renamed"]),
                   old=(old or {}).get("id", "-")))
    if d["renamed"]:
        out.print_table([[dom + ":" + c, a, b] for dom, c, a, b in
                         d["renamed"][:200]],
                        columns=[t("col.code"), t("col.before"),
                                 t("col.after")])
    lost = []
    if doc is not None and not doc.IsFamilyDocument:
        for (tn, code), n in sorted(util.used_codes(doc).items()):
            dom = {"L": "L", "A": "S", "B": "S", "E": "E"}.get(tn)
            if dom and code not in new["domains"].get(dom, {}):
                lost.append(("[%s]%s" % (tn, code), n))
    if lost:
        out.print_md("### " + t("table.lost", n=len(lost)))
        out.print_table([[c, n] for c, n in lost],
                        columns=[t("col.code"), t("col.count")])
    if not ui.confirm("table.confirm", id=new["id"], lost=len(lost)):
        return
    tid = store.save_table(new, source)
    ui.alert("table.saved", id=tid, folder=store.user)


def from_link():
    cfg = store.config()
    text = forms.ask_for_string(default=cfg.get("table_link", ""),
                                prompt=t("table.link_prompt"),
                                title=t("table.title"))
    links = importer.split_links(text)
    if not links:
        return
    paths, problems = download.fetch(links)
    for key, p in problems:
        ui.alert(key, **p)
    if not paths:
        return
    store.save_config(table_link=" ".join(links))
    load_and_confirm(paths, " ".join(links))


def from_files():
    paths = forms.pick_file(files_filter="CCI (*.xlsx;*.json)|*.xlsx;*.json",
                            multi_file=True, title=t("table.pick_files"))
    if not paths:
        return
    if not isinstance(paths, (list, tuple)):
        paths = [paths]
    load_and_confirm(list(paths), "; ".join(os.path.basename(p)
                                             for p in paths))


def switch():
    ids = sorted(store.table_ids())
    if len(ids) < 2:
        ui.alert("table.only_one")
        return
    current = store.active_id()
    labels = [("● " if i == current else "   ") + i for i in ids]
    picked = forms.SelectFromList.show(labels, title=t("table.switch"),
                                       button_name=t("btn.select"))
    if not picked:
        return
    store.set_active(ids[labels.index(picked)])
    ui.alert("table.switched", id=ids[labels.index(picked)])


def export_names():
    table = store.load_table()
    path = forms.save_file(file_ext="csv", default_name=t("table.csv_name"))
    if not path:
        return
    with codecs.open(path, "w", "utf-8") as f:
        f.write(importer.names_csv(table.data, store.names()))
    ui.alert("table.exported", path=path)
    script.show_file_in_explorer(path)


def import_names():
    path = forms.pick_file(file_ext="csv", title=t("table.pick_csv"))
    if not path:
        return
    table = store.load_table()
    try:
        names = importer.read_names_csv(path, table.data)
    except importer.ImportError_ as ex:
        ui.alert(ex.key, **ex.params)
        return
    n = store.save_names(names)
    ui.alert("table.imported_names", n=n, folder=store.user)


def folder():
    if not ui.confirm("table.folder_now", path=store.user):
        return
    path = forms.pick_folder(title=t("table.pick_folder"))
    if path:
        util.set_data_folder(path)
        ui.alert("table.folder_set", path=path)


ACTIONS = {"info": info, "link": from_link, "files": from_files,
           "switch": switch, "export": export_names, "import": import_names,
           "folder": folder}

labels = [t("table.opt_" + o) for o in OPTIONS]
choice = forms.CommandSwitchWindow.show(labels, message=t("table.choose"))
if choice:
    ACTIONS[OPTIONS[labels.index(choice)]]()
