# -*- coding: utf-8 -*-
"""Classify: propose a CCI class for every type (and room name), let the
person check and edit, then write CCIClassCode, CCITopnode and
CCIClassification."""
from __future__ import unicode_literals

import os

from pyrevit import forms, revit, script

from cci import formats, groups, numbering
from cci import table as cci_table
from cci.i18n import t
from cci.revit import storage, ui, util

doc = ui.doc()
ui.require_project(doc)
settings = ui.settings_or_warn(doc)
ruleset = util.load_rules(settings)
table = util.load_classes()
LANG = ui.lang()


class Row(forms.Reactive):

    def __init__(self, key, kind, category, name, elements, etype, result,
                 current, bic, family, type_name):
        self.key = key
        self.kind = kind
        self.category = category
        self.name = name
        self.bic = bic
        self.family = family
        self.type_name = type_name
        self.elements = elements
        self.etype = etype
        self.count = len(elements)
        self.topnode = result.topnode
        self.rule = result
        self.current = current or ""
        if result.class_code:
            self.suggested = result.class_code
        elif result.source == "pending":
            self.suggested = t("classify.pending")
        else:
            self.suggested = ""
        if result.studio:
            self.source = t("classify.src_studio")
        elif result.verified:
            self.source = t("classify.src_guide")
        elif result.class_code:
            self.source = t("classify.src_tool")
        else:
            self.source = ""
        self._include = True
        self._remember = False
        self._code = current if current and current != "*" \
            else (result.class_code or "")
        self._u = result.u or ""
        self._vv = result.vv or ""

    @forms.reactive
    def include(self):
        return self._include

    @include.setter
    def include(self, value):
        self._include = bool(value)

    @forms.reactive
    def remember(self):
        return self._remember

    @remember.setter
    def remember(self, value):
        self._remember = bool(value)

    @property
    def domain_topnode(self):
        return "[%s]" % self.topnode

    @forms.reactive
    def code(self):
        return self._code

    @code.setter
    def code(self, value):
        self._code = formats.norm(value)
        try:
            self.OnPropertyChanged("class_name")
        except Exception:
            pass

    @forms.reactive
    def u(self):
        return self._u

    @u.setter
    def u(self, value):
        self._u = formats.norm(value)

    @forms.reactive
    def vv(self):
        return self._vv

    @vv.setter
    def vv(self, value):
        self._vv = formats.norm(value)

    @property
    def class_name(self):
        if not self._code:
            return ""
        if formats.check_class(self._code):
            return t("classify.bad_code")
        name = table.name(self._code, LANG, self.domain_topnode)
        if not name:
            return t("classify.not_in_table")
        return name


def collect():
    selected = revit.get_selection().elements
    elements = selected if selected else util.classified_instances(doc)
    rows = {}
    for e in elements:
        cat = util.bic_name(e)
        if cat not in groups.all_categories():
            continue
        kind = groups.kind_of(cat)
        if kind == "space":
            if not util.is_placed_space(e):
                continue
            room_name = util.get(e, "Name") or ""
            key = "space|%s|%s" % (cat, room_name)
            etype = None
        else:
            etype = util.element_type(doc, e)
            if etype is None:
                continue
            key = etype.UniqueId
        row = rows.get(key)
        if row is None:
            res = ruleset.classify(util.facts(doc, e, etype), kind)
            if kind == "space":
                name = room_name
                current = util.get_key(e, "class") or ""
            else:
                name = "%s : %s" % (util.family_name(etype),
                                    util.type_name(etype))
                current = util.get_key(etype, "class_t") or ""
            rows[key] = Row(key, kind, e.Category.Name, name, [e], etype,
                            res, current, cat,
                            util.family_name(etype) if etype else "",
                            util.type_name(etype) if etype else room_name)
        else:
            row.elements.append(e)
            if kind == "space":
                cur = util.get_key(e, "class") or ""
                if cur != row.current:
                    row.current = "*"
    out = list(rows.values())
    out.sort(key=lambda r: (bool(r.current), r.category, r.name))
    return out, bool(selected)


class ClassifyWindow(forms.WPFWindow):

    def __init__(self, rows, from_selection):
        forms.WPFWindow.__init__(
            self, os.path.join(os.path.dirname(__file__), "ui.xaml"))
        self.rows = rows
        self.ok = False
        self.Title = t("classify.title")
        self.intro.Text = t("classify.intro_sel" if from_selection
                            else "classify.intro")
        self.search_l.Text = t("classify.search")
        self.only_missing_cb.Content = t("classify.only_missing")
        self.use_rules_b.Content = t("classify.use_rules")
        self.pick_b.Content = t("classify.pick")
        self.write_b.Content = t("classify.write")
        self.cancel_b.Content = t("btn.cancel")
        heads = ["", "classify.col_category", "classify.col_name",
                 "classify.col_count", "classify.col_current",
                 "classify.col_suggested", "classify.col_source",
                 "classify.col_code", "classify.col_u", "classify.col_vv",
                 "classify.col_class_name", "classify.col_remember"]
        for col, key in zip(self.grid.Columns, heads):
            col.Header = t(key) if key else ""
        self.grid.ItemsSource = rows
        self._status()

    def _status(self):
        done = sum(1 for r in self.rows if r.code)
        self.status.Text = t("classify.status", done=done,
                             total=len(self.rows))

    def search_changed(self, sender, args):
        text = (self.search_tb.Text or "").lower()
        only = bool(self.only_missing_cb.IsChecked)
        self.grid.ItemsSource = [
            r for r in self.rows
            if (not text or text in (r.name + " " + r.category).lower())
            and (not only or not r.code)]

    def use_rules_click(self, sender, args):
        for r in self.grid.SelectedItems or []:
            if r.rule.class_code:
                r.code = r.rule.class_code
                r.u = r.rule.u or ""
                r.vv = r.rule.vv or ""
        self.grid.Items.Refresh()
        self._status()

    def pick_click(self, sender, args):
        """Pick a class from the CCI table for the selected rows."""
        selected = list(self.grid.SelectedItems or [])
        if not selected:
            forms.alert(t("classify.select_rows"), title=t("classify.title"))
            return
        top = selected[0].domain_topnode
        domain = cci_table.domain_for(top)
        same = [r for r in selected if cci_table.domain_for(
            r.domain_topnode) == domain]
        choices = table.choices(domain, LANG)
        if not choices:
            forms.alert(t("classify.no_table"), title=t("classify.title"))
            return
        labels = ["%s   %s" % (c, label) for c, label in choices]
        picked = forms.SelectFromList.show(
            labels, title=t("classify.pick_title", n=len(same)),
            button_name=t("btn.select"), width=640, height=640)
        if not picked:
            return
        code = choices[labels.index(picked)][0]
        for r in same:
            r.code = code
        self.grid.Items.Refresh()
        self._status()

    def write_click(self, sender, args):
        bad = [r for r in self.rows
               if r.include and r.code and formats.check_class(r.code)]
        bad += [r for r in self.rows if r.include and r.code
                and ((r.u and len(r.u) != 1) or (r.vv and len(r.vv) != 2))]
        if bad:
            forms.alert(t("classify.fix_codes") + "\n\n" + "\n".join(
                "%s: %s" % (r.name, r.code) for r in bad[:15]),
                title=t("classify.title"))
            return
        self.ok = True
        self.Close()


def write(rows):
    copy = settings["copy_to_instance"]
    registry = storage.load_registry(doc)
    stats = {"types": 0, "spaces": 0, "not_bound": 0}
    for r in rows:
        if not r.include or not r.code:
            continue
        tn = formats.topnode(r.topnode) if settings["write_topnode"] else None
        cls = formats.classification(
            r.topnode if settings["classification_with_topnode"] else None,
            r.code) if settings["write_classification"] else None
        if r.kind == "space":
            for room in r.elements:
                if not util.has_key(room, "class"):
                    stats["not_bound"] += 1
                    continue
                util.set_key(room, "class", r.code)
                if tn:
                    util.set_key(room, "topnode", tn)
                if cls:
                    util.set_key(room, "classification", cls)
                stats["spaces"] += 1
            continue
        etype = r.etype
        if not util.has_key(etype, "class_t"):
            stats["not_bound"] += 1
            continue
        new = {"class": r.code}
        if tn:
            new["topnode"] = tn
        if cls:
            new["classification"] = cls
        old = dict((k, util.get_key(etype, k + "_t") or "") for k in new)
        for k, v in new.items():
            util.set_key(etype, k + "_t", v)
        for inst in r.elements:
            for k, v in new.items():
                if not util.has_key(inst, k):
                    continue
                value = numbering.resolve_instance(
                    util.get_key(inst, k), old[k], v, copy)
                if value is not None:
                    util.set_key(inst, k, value)
        if r.u and r.vv:
            registry.parents[r.key] = {"u": r.u, "vv": r.vv}
        else:
            registry.parents.pop(r.key, None)
        stats["types"] += 1
    storage.save_registry(doc, registry)
    if table.id:
        s = storage.load_settings(doc)
        if s.get("table_id") != table.id:
            s["table_id"] = table.id
            storage.save_settings(doc, s)
    return stats


def remember(rows):
    """Save ticked rows as studio rules (exact family and type, or room
    name), so the next project gets the same class."""
    st = util.store()
    n = 0
    for r in rows:
        if not (r.include and r.remember and r.code):
            continue
        match = {"type": r.type_name}
        if r.kind != "space":
            match["family"] = r.family
        rule = {"id": "studio:%s:%s:%s" % (r.bic, r.family, r.type_name),
                "category": [r.bic], "match": match, "class": r.code,
                "note": "Classify"}
        if r.u and r.vv:
            rule["u"], rule["vv"] = r.u, r.vv
        st.add_rule(rule)
        n += 1
    return n


rows, from_selection = collect()
if not rows:
    ui.alert("classify.nothing", exit=True)
win = ClassifyWindow(rows, from_selection)
win.ShowDialog()
if not win.ok:
    script.exit()

with ui.Tx(doc, "tx.classify"):
    stats = write(rows)
remembered = remember(rows)

msg = t("classify.done", types=stats["types"], spaces=stats["spaces"])
if remembered:
    msg += "\n\n" + t("classify.remembered", n=remembered)
if stats["not_bound"]:
    msg += "\n\n" + t("classify.not_bound", n=stats["not_bound"])
forms.alert(msg, title=t("classify.title"))
