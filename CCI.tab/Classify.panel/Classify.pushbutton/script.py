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
        self.inst_codes = set()     # other codes set on single elements

    @property
    def instance_only(self):
        """Rooms, and elements without a type: values go on the elements."""
        return self.kind == "space" or self.etype is None

    @property
    def count(self):
        return len(self.elements)

    @property
    def outdated(self):
        """Existing code that is malformed or not in the CCI table."""
        cur = self.current
        if not cur or cur == "*":
            return False
        return bool(formats.check_class(cur)) or \
            not table.known(cur, self.domain_topnode)

    @property
    def differs(self):
        """Existing code differs from the suggestion."""
        cur = self.current
        return bool(self.rule.class_code and cur and cur != "*"
                    and cur != self.rule.class_code)

    @property
    def old_coding(self):
        return self.outdated or self.differs or bool(self.inst_codes) \
            or self.current == "*"

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


def expand(selected):
    """Selected elements, with model groups and assemblies opened up to
    their members (selecting a group selects the group, not its walls)."""
    out = []
    for e in selected:
        get_members = getattr(e, "GetMemberIds", None)
        if get_members is not None:
            try:
                out.extend(doc.GetElement(i) for i in get_members())
                continue
            except Exception:
                pass
        out.append(e)
    return [e for e in out if e is not None]


def collect(use_selection=True):
    selected = expand(revit.get_selection().elements) if use_selection \
        else []
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
                # shaft openings and other elements without a type: one
                # row per category, written on the elements themselves
                key = "notype|%s" % cat
            else:
                key = etype.UniqueId
        row = rows.get(key)
        if row is None:
            res = ruleset.classify(util.facts(doc, e, etype), kind)
            if kind == "space":
                name = room_name
                current = util.get_key(e, "class") or ""
            elif etype is None:
                name = e.Category.Name
                current = util.get_key(e, "class") or ""
            else:
                name = "%s : %s" % (util.family_name(etype),
                                    util.type_name(etype))
                current = util.get_key(etype, "class_t") or ""
            rows[key] = Row(key, kind, e.Category.Name, name, [e], etype,
                            res, current, cat,
                            util.family_name(etype) if etype else "",
                            util.type_name(etype) if etype else
                            (room_name if kind == "space" else ""))
        else:
            row.elements.append(e)
            if row.instance_only:
                cur = util.get_key(e, "class") or ""
                if cur != row.current:
                    row.current = "*"
    out = list(rows.values())
    for r in out:
        if r.instance_only:
            continue
        for e in r.elements:
            v = util.get_key(e, "class") or ""
            if v and v != r.current:
                r.inst_codes.add(v)
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
        self.only_diff_cb.Content = t("classify.only_old")
        self.replace_b.Content = t("classify.replace_old")
        self.reset_inst_cb.Content = t("classify.reset_instances")
        self.reset_instances = False
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
        # Escape no longer closes the window, and closing it (Cancel or
        # the X) asks first when something was changed
        self._start = self._state()
        self.Closing += self.on_closing

    def _state(self):
        return [(r.code, r.include, r.u, r.vv, r.remember)
                for r in self.rows]

    def cancel_click(self, sender, args):
        self.Close()

    def on_closing(self, sender, args):
        if self.ok or self._state() == self._start:
            return
        if not forms.alert(t("msg.discard_changes"), title=t("app.name"),
                           yes=True, no=True):
            args.Cancel = True

    def _status(self):
        done = sum(1 for r in self.rows if r.code)
        old = sum(1 for r in self.rows if r.old_coding)
        self.status.Text = t("classify.status", done=done,
                             total=len(self.rows), old=old)

    def search_changed(self, sender, args):
        text = (self.search_tb.Text or "").lower()
        only = bool(self.only_missing_cb.IsChecked)
        only_old = bool(self.only_diff_cb.IsChecked)
        self.grid.ItemsSource = [
            r for r in self.rows
            if (not text or text in (r.name + " " + r.category).lower())
            and (not only or not r.code)
            and (not only_old or r.old_coding)]

    def replace_click(self, sender, args):
        """Replace old coding with the suggestion: selected rows, or every
        row with old coding when nothing is selected."""
        selected = list(self.grid.SelectedItems or [])
        rows = selected or [r for r in self.rows if r.old_coding]
        n = 0
        for r in rows:
            if r.rule.class_code and r.code != r.rule.class_code:
                r.code = r.rule.class_code
                r.u = r.rule.u or ""
                r.vv = r.rule.vv or ""
                n += 1
        if any(r.inst_codes for r in rows):
            self.reset_inst_cb.IsChecked = True
        no_sugg = sum(1 for r in rows if r.old_coding and
                      not r.rule.class_code)
        self.grid.Items.Refresh()
        self._status()
        forms.alert(t("classify.replaced", n=n, left=no_sugg),
                    title=t("classify.title"))

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
        self.reset_instances = bool(self.reset_inst_cb.IsChecked)
        self.ok = True
        self.Close()


def write(rows, reset_instances=False):
    """reset_instances: also replace codes set on single elements (old
    coding), not only empty values and copies of the old type value."""
    copy = settings["copy_to_instance"]
    registry = storage.load_registry(doc)
    stats = {"types": 0, "spaces": 0, "not_bound": 0}
    for r in rows:
        if not r.include or not r.code:
            continue
        tn = formats.topnode(r.topnode) if settings["write_topnode"] else None
        entry = table.entry(r.code, r.domain_topnode) or {}
        en_name = entry.get("en", "")
        cls = formats.classification(
            r.code, en_name if settings["classification_desc"] else None) \
            if settings["write_classification"] else None
        # filled only where the template has these parameters
        extra = {"class_name": en_name,
                 "class_version": table.data.get("edition", "")}
        if r.instance_only:
            for room in r.elements:
                if not util.has_key(room, "class"):
                    stats["not_bound"] += 1
                    continue
                util.set_key(room, "class", r.code)
                if tn:
                    util.set_key(room, "topnode", tn)
                if cls:
                    util.set_key(room, "classification", cls)
                for k, v in extra.items():
                    if v and util.has_key(room, k):
                        util.set_key(room, k, v)
                if r.kind == "space":
                    stats["spaces"] += 1
                else:
                    stats["types"] += 1
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
        for k, v in extra.items():
            if v and util.has_key(etype, k + "_t"):
                new[k] = v
        old = dict((k, util.get_key(etype, k + "_t") or "") for k in new)
        for k, v in new.items():
            util.set_key(etype, k + "_t", v)
        for inst in r.elements:
            for k, v in new.items():
                if not util.has_key(inst, k):
                    continue
                if reset_instances:
                    value = v if copy else ""
                else:
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
        rule = {"id": "studio:%s:%s:%s" % (r.bic, r.family, r.type_name),
                "category": [r.bic], "class": r.code, "note": "Classify"}
        if r.kind == "space":
            rule["match"] = {"type": r.type_name}
        elif r.etype is not None:
            rule["match"] = {"family": r.family, "type": r.type_name}
        # no type: the rule covers the whole category
        if r.u and r.vv:
            rule["u"], rule["vv"] = r.u, r.vv
        st.add_rule(rule)
        n += 1
    return n


rows, from_selection = collect()
if not rows and from_selection:
    # the selection held nothing to classify (a view, tags, lines, a
    # linked model...): use the whole model instead
    rows, from_selection = collect(use_selection=False)
if not rows:
    ui.alert("classify.nothing", exit=True)
win = ClassifyWindow(rows, from_selection)
win.ShowDialog()
if not win.ok:
    script.exit()

with ui.Tx(doc, "tx.classify"):
    stats = write(rows, win.reset_instances)
remembered = remember(rows)

msg = t("classify.done", types=stats["types"], spaces=stats["spaces"])
if remembered:
    msg += "\n\n" + t("classify.remembered", n=remembered)
if stats["not_bound"]:
    msg += "\n\n" + t("classify.not_bound", n=stats["not_bound"])
forms.alert(msg, title=t("classify.title"))
