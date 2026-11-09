# -*- coding: utf-8 -*-
"""Shared bits for the buttons: messages, transactions, output."""
from __future__ import unicode_literals

from pyrevit import forms, revit, script

from cci import i18n
from cci.i18n import t
from cci.revit import storage


def doc():
    return revit.doc


def output():
    out = script.get_output()
    out.set_title(t("app.name"))
    return out


def alert(key, exit=False, **params):
    forms.alert(t(key, **params), title=t("app.name"), exitscript=exit)


def confirm(key, **params):
    return forms.alert(t(key, **params), title=t("app.name"),
                       yes=True, no=True)


def require_project(d):
    if d is None or d.IsFamilyDocument:
        alert("msg.need_project", exit=True)
    from cci.revit import util
    util.use_project_names(d)


def settings_or_warn(d):
    """Project settings; warns once if Setup was never run."""
    if not storage.has_settings(d):
        if not confirm("msg.no_setup"):
            script.exit()
    return storage.load_settings(d)


class Tx(object):
    """with Tx(doc, 'tx.classify'): ...  (name translated)"""

    def __init__(self, d, key):
        self._tx = revit.Transaction(t(key), doc=d)

    def __enter__(self):
        return self._tx.__enter__()

    def __exit__(self, *exc):
        return self._tx.__exit__(*exc)


def link(out, element_id_int):
    from Autodesk.Revit.DB import ElementId
    from System import Int64
    try:
        return out.linkify(ElementId(Int64(element_id_int)))
    except Exception:
        return str(element_id_int)


def project_name(d):
    """Project Name from Project Information, else the file's title."""
    name = ""
    try:
        name = (d.ProjectInformation.Name or "").strip()
    except Exception:
        pass
    if not name or name.lower() in ("project name", "heiti verkefnis"):
        try:
            name = d.Title or ""
        except Exception:
            name = ""
    if name.lower().endswith(".rvt"):
        name = name[:-4]
    return name


def file_name(label, d):
    """'CCI-athugun_<project>_2026-11-09': label, project, date; safe for
    Windows file names."""
    import datetime
    import re
    parts = [label, project_name(d), datetime.date.today().isoformat()]
    name = "_".join(p for p in parts if p)
    return re.sub(r'[\\/:*?"<>|]+', "-", name).strip()


def lang():
    return i18n.lang()
