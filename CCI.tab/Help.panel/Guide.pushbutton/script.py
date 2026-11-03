# -*- coding: utf-8 -*-
"""Leiðbeiningar / Guide: a window with tabs explaining how to use the
tool, what CCI is, the parameters and their values, LOD, scope, common
problems, a searchable CCI table and a glossary."""
from __future__ import unicode_literals

import os

from pyrevit import forms, revit

from System.Windows import FontWeights, Thickness, TextWrapping
from System.Windows import GridLength, GridUnitType, TextMarkerStyle
from System.Windows import VerticalAlignment
from System.Windows.Controls import (
    Button, ColumnDefinition, ComboBox, DockPanel, FlowDocumentScrollViewer,
    Grid, ListBox, Orientation, RowDefinition, ScrollViewer, StackPanel,
    TabItem, TextBlock, TextBox, Dock, ScrollBarVisibility)
from System.Windows.Documents import (
    Bold, FlowDocument, Italic, List, ListItem, Paragraph, Run, Section,
    Table, TableCell, TableColumn, TableRow, TableRowGroup)
from System.Windows.Media import BrushConverter, FontFamily

from cci import formats, guide
from cci.i18n import t
from cci.revit import ui, util

LANG = ui.lang()
_BC = BrushConverter()


def brush(hexcode):
    return _BC.ConvertFromString(hexcode)


ACCENT = "#5B4B8A"
MONO = FontFamily("Consolas")


# ---------------------------------------------------------- FlowDocument

def add_inline(inlines, text):
    for kind, part in guide.inline(text):
        run = Run(part)
        if kind == "b":
            inlines.Add(Bold(run))
        elif kind == "i":
            inlines.Add(Italic(run))
        elif kind == "c":
            run.FontFamily = MONO
            run.Background = brush("#F1EEF8")
            inlines.Add(run)
        else:
            inlines.Add(run)


def para(text, size=None, bold=False, colour=None, margin=None):
    p = Paragraph()
    add_inline(p.Inlines, text)
    if size:
        p.FontSize = size
    if bold:
        p.FontWeight = FontWeights.SemiBold
    if colour:
        p.Foreground = brush(colour)
    if margin:
        p.Margin = Thickness(*margin)
    return p


def box(text, back, edge):
    s = Section()
    s.Background = brush(back)
    s.BorderBrush = brush(edge)
    s.BorderThickness = Thickness(4, 0, 0, 0)
    s.Padding = Thickness(10, 6, 10, 6)
    s.Margin = Thickness(0, 6, 0, 10)
    s.Blocks.Add(para(text, margin=(0, 0, 0, 0)))
    return s


def make_list(items, numbered):
    lst = List()
    lst.MarkerStyle = (TextMarkerStyle.Decimal if numbered else
                       TextMarkerStyle.Disc)
    lst.Margin = Thickness(0, 0, 0, 10)
    for item in items:
        lst.ListItems.Add(ListItem(para(item, margin=(0, 2, 0, 2))))
    return lst


def make_table(head, rows):
    tbl = Table()
    tbl.CellSpacing = 0
    tbl.BorderBrush = brush("#D9D4E6")
    tbl.BorderThickness = Thickness(1)
    tbl.Margin = Thickness(0, 4, 0, 12)
    for _ in head:
        tbl.Columns.Add(TableColumn())
    group = TableRowGroup()
    tbl.RowGroups.Add(group)

    def add_row(cells, header):
        r = TableRow()
        if header:
            r.Background = brush("#EDE9F5")
        elif group.Rows.Count % 2 == 0:
            r.Background = brush("#FAF9FC")
        for c in cells:
            cell = TableCell(para("%s" % c, bold=header,
                                  margin=(0, 0, 0, 0)))
            cell.Padding = Thickness(8, 4, 8, 4)
            cell.BorderBrush = brush("#E6E2EF")
            cell.BorderThickness = Thickness(0, 0, 0, 1)
            r.Cells.Add(cell)
        group.Rows.Add(r)

    add_row(head, True)
    for row in rows:
        add_row(row, False)
    return tbl


def document(blocks):
    doc = FlowDocument()
    doc.FontFamily = FontFamily("Segoe UI")
    doc.FontSize = 13.5
    doc.PagePadding = Thickness(28, 18, 28, 24)
    doc.LineHeight = 20
    for b in blocks:
        kind = b["t"]
        if kind == "h2":
            doc.Blocks.Add(para(b["text"], 22, True, ACCENT, (0, 0, 0, 8)))
        elif kind == "h3":
            doc.Blocks.Add(para(b["text"], 16, True, "#333333",
                                (0, 14, 0, 4)))
        elif kind == "p":
            doc.Blocks.Add(para(b["text"], margin=(0, 0, 0, 8)))
        elif kind == "note":
            doc.Blocks.Add(box(b["text"], "#EEF6F0", "#3C8D5A"))
        elif kind == "warn":
            doc.Blocks.Add(box(b["text"], "#FDF3E6", "#C77B1A"))
        elif kind == "code":
            p = Paragraph(Run(b["text"]))
            p.FontFamily = MONO
            p.FontSize = 12.5
            p.Background = brush("#F5F4F8")
            p.Padding = Thickness(10, 8, 10, 8)
            p.Margin = Thickness(0, 4, 0, 10)
            doc.Blocks.Add(p)
        elif kind in ("ul", "ol"):
            doc.Blocks.Add(make_list(b["items"], kind == "ol"))
        elif kind == "table":
            doc.Blocks.Add(make_table(b["head"], b["rows"]))
    return doc


def doc_view(blocks):
    v = FlowDocumentScrollViewer()
    v.Document = document(blocks)
    v.VerticalScrollBarVisibility = ScrollBarVisibility.Auto
    return v


# ----------------------------------------------------------- model status

def model_info(d):
    from cci.revit import params, storage
    info = {"setup": False, "params": (0, 0), "types": (0, 0),
            "type_ids": (0, 0), "rooms": (0, 0)}
    if d is None or d.IsFamilyDocument:
        return None
    util.use_project_names(d)
    info["setup"] = storage.has_settings(d)
    have = set(n.lower() for n in params.bound_names(d))
    need = [formats.PARAM[k] for k in formats.REQUIRED_PARAMS]
    info["params"] = (len([n for n in need if n.lower() in have]),
                      len(need))
    types = {}
    rooms = [0, 0]
    rooms_cls = [0, 0]
    for e in util.classified_instances(d):
        try:
            kind = util.group_and_kind(d, e)[1]
        except Exception:
            continue
        if kind == "space":
            rooms[1] += 1
            rooms_cls[1] += 1
            if util.get_key(e, "ml_location_id"):
                rooms[0] += 1
            if util.get_key(e, "class"):
                rooms_cls[0] += 1
            continue
        et = util.element_type(d, e)
        if et is None:
            continue
        key = util.eid(et)
        if key not in types:
            types[key] = (bool(util.get_key(et, "class_t") or
                               util.get_key(e, "class")),
                          bool(util.get_key(et, "type_id_t") or
                               util.get_key(e, "type_id")))
    info["types"] = (len([1 for c, _ in types.values() if c]) +
                     rooms_cls[0], len(types) + rooms_cls[1])
    info["type_ids"] = (len([1 for _, i in types.values() if i]),
                        len(types))
    info["rooms"] = tuple(rooms)
    return info


# ----------------------------------------------------------------- window

class GuideWindow(forms.WPFWindow):

    def __init__(self):
        forms.WPFWindow.__init__(
            self, os.path.join(os.path.dirname(__file__), "ui.xaml"))
        self.Title = t("guide.title")
        self.head_t.Text = t("guide.title")
        self.head_s.Text = t("guide.subtitle")
        self.close_b.Content = t("guide.close")
        try:
            self.ct = util.load_classes()
        except Exception:
            self.ct = None
        self.foot_t.Text = t("guide.footer", table=(
            self.ct.title if self.ct is not None and self.ct.id else "-"))
        for page in guide.pages(LANG, self.ct):
            tab = TabItem()
            tab.Header = page["title"]
            if page["id"] == "browser":
                tab.Content = self.browser()
            elif page["id"] == "steps":
                tab.Content = self.steps_view(page["blocks"])
            else:
                tab.Content = doc_view(page["blocks"])
            self.tabs.Items.Add(tab)
        self.tabs.SelectedIndex = 0

    # ------------------------------------------------ steps + status
    def steps_view(self, blocks):
        panel = DockPanel()
        bar = StackPanel()
        bar.Orientation = Orientation.Horizontal
        bar.Margin = Thickness(28, 12, 28, 0)
        b = Button()
        b.Content = t("guide.status_b")
        b.Padding = Thickness(10, 4, 10, 4)
        b.Click += self.status_click
        bar.Children.Add(b)
        hint = TextBlock()
        hint.Text = t("guide.status_d")
        hint.Foreground = brush("#666666")
        hint.Margin = Thickness(12, 0, 0, 0)
        hint.VerticalAlignment = VerticalAlignment.Center
        hint.TextWrapping = TextWrapping.Wrap
        bar.Children.Add(hint)
        DockPanel.SetDock(bar, Dock.Top)
        panel.Children.Add(bar)
        self.status_panel = StackPanel()
        self.status_panel.Margin = Thickness(28, 8, 28, 0)
        DockPanel.SetDock(self.status_panel, Dock.Top)
        panel.Children.Add(self.status_panel)
        panel.Children.Add(doc_view(blocks))
        return panel

    def status_click(self, sender, args):
        self.status_panel.Children.Clear()
        try:
            info = model_info(revit.doc)
        except Exception as ex:
            info = None
            self.add_status_line("!", "%s" % ex, "#B03A2E")
        if info is None:
            self.add_status_line("·", t("guide.status_none"), "#666666")
            return
        guide.LANG[0] = LANG
        for name, done, detail in guide.model_status(info):
            if done is True:
                self.add_status_line("✓", "%s: %s" % (name, detail),
                                     "#2E7D4F")
            elif done is False:
                self.add_status_line("✗", "%s: %s" % (name, detail),
                                     "#B03A2E")
            else:
                self.add_status_line("·", "%s: %s" % (name, detail),
                                     "#666666")

    def add_status_line(self, mark, text, colour):
        tb = TextBlock()
        tb.Text = "%s  %s" % (mark, text)
        tb.Foreground = brush(colour)
        tb.FontWeight = FontWeights.SemiBold
        tb.Margin = Thickness(0, 1, 0, 1)
        self.status_panel.Children.Add(tb)

    # ------------------------------------------------------ browser
    def browser(self):
        guide.LANG[0] = LANG
        grid = Grid()
        grid.Margin = Thickness(16)
        for h in (GridLength.Auto, GridLength.Auto,
                  GridLength(1, GridUnitType.Star)):
            rd = RowDefinition()
            rd.Height = h
            grid.RowDefinitions.Add(rd)
        for w in (GridLength(2, GridUnitType.Star),
                  GridLength(3, GridUnitType.Star)):
            cd = ColumnDefinition()
            cd.Width = w
            grid.ColumnDefinitions.Add(cd)

        intro = TextBlock()
        intro.Text = t("guide.browser_d")
        intro.TextWrapping = TextWrapping.Wrap
        intro.Margin = Thickness(0, 0, 0, 10)
        Grid.SetColumnSpan(intro, 2)
        grid.Children.Add(intro)

        bar = StackPanel()
        bar.Orientation = Orientation.Horizontal
        bar.Margin = Thickness(0, 0, 0, 8)
        self.dom_cb = ComboBox()
        self.dom_cb.MinWidth = 200
        for dom, _ in guide.BROWSER_DOMAINS:
            self.dom_cb.Items.Add(guide.domain_label(dom))
        self.dom_cb.SelectedIndex = 0
        self.dom_cb.SelectionChanged += self.browse_changed
        bar.Children.Add(self.dom_cb)
        lbl = TextBlock()
        lbl.Text = t("classify.search")
        lbl.Margin = Thickness(14, 0, 6, 0)
        lbl.VerticalAlignment = VerticalAlignment.Center
        bar.Children.Add(lbl)
        self.find_tb = TextBox()
        self.find_tb.Width = 260
        self.find_tb.TextChanged += self.browse_changed
        bar.Children.Add(self.find_tb)
        self.count_t = TextBlock()
        self.count_t.Foreground = brush("#666666")
        self.count_t.Margin = Thickness(12, 0, 0, 0)
        self.count_t.VerticalAlignment = VerticalAlignment.Center
        bar.Children.Add(self.count_t)
        Grid.SetRow(bar, 1)
        Grid.SetColumnSpan(bar, 2)
        grid.Children.Add(bar)

        self.list_lb = ListBox()
        self.list_lb.FontFamily = MONO
        self.list_lb.SelectionChanged += self.pick_changed
        Grid.SetRow(self.list_lb, 2)
        grid.Children.Add(self.list_lb)

        sv = ScrollViewer()
        sv.VerticalScrollBarVisibility = ScrollBarVisibility.Auto
        sv.Margin = Thickness(12, 0, 0, 0)
        self.detail = StackPanel()
        sv.Content = self.detail
        Grid.SetRow(sv, 2)
        Grid.SetColumn(sv, 1)
        grid.Children.Add(sv)

        self._codes = []
        if self.ct is None or not self.ct.id:
            self.count_t.Text = t("classify.no_table")
        else:
            self.fill_list()
        return grid

    def domain(self):
        i = max(0, self.dom_cb.SelectedIndex)
        return guide.BROWSER_DOMAINS[i][0]

    def fill_list(self):
        if self.ct is None:
            return
        dom = self.domain()
        hits = self.ct.search(self.find_tb.Text, dom, LANG, limit=2000)
        self._codes = [c for c, _ in hits]
        self.list_lb.Items.Clear()
        for code, label in hits:
            self.list_lb.Items.Add("%-4s  %s" % (code, label))
        self.count_t.Text = t("guide.browser_count", n=len(hits))

    def browse_changed(self, sender, args):
        self.fill_list()

    def pick_changed(self, sender, args):
        self.detail.Children.Clear()
        i = self.list_lb.SelectedIndex
        if i < 0 or i >= len(self._codes):
            return
        for label, value in guide.browser_detail(
                self.ct, self.domain(), self._codes[i], LANG):
            k = TextBlock()
            k.Text = label
            k.Foreground = brush(ACCENT)
            k.FontWeight = FontWeights.SemiBold
            k.Margin = Thickness(0, 6, 0, 0)
            self.detail.Children.Add(k)
            v = TextBox()
            v.Text = value
            v.IsReadOnly = True
            v.BorderThickness = Thickness(0)
            v.Background = brush("#FFFFFF")
            v.TextWrapping = TextWrapping.Wrap
            self.detail.Children.Add(v)

    def close_click(self, sender, args):
        self.Close()


GuideWindow().ShowDialog()
