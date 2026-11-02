# -*- coding: utf-8 -*-
"""Project setup: scope, building/storey codes, LOD, code options."""
from __future__ import unicode_literals

import os

from pyrevit import forms
from Autodesk.Revit.DB import FilteredElementCollector, Level, UnitUtils, \
    UnitTypeId

from cci import formats, groups, levels as levels_mod, settings as smod
from cci.i18n import t
from cci.revit import storage, ui

doc = ui.doc()
ui.require_project(doc)

LOD_OPTIONS = ["200", "300", "325", "400"]
ROOM_MODES = ["as_is", "last_segment", "auto"]
DOOR_ROOMS = ["to", "from"]
ML_NUMBERS = ["type", "instance"]
PADS = ["2", "3", "4"]


class LevelRow(forms.Reactive):
    def __init__(self, name, elevation_m, code):
        self.name = name
        self.elevation = "%.2f" % elevation_m
        self._code = code or ""

    @forms.reactive
    def code(self):
        return self._code

    @code.setter
    def code(self, value):
        self._code = formats.norm(value)


class LodRow(forms.Reactive):
    def __init__(self, gid, lod):
        self.gid = gid
        self.name = t("group." + gid)
        self.options = LOD_OPTIONS
        self._lod = str(lod)

    @forms.reactive
    def lod(self):
        return self._lod

    @lod.setter
    def lod(self, value):
        self._lod = value


def project_levels():
    out = []
    for lv in FilteredElementCollector(doc).OfClass(Level):
        elev = UnitUtils.ConvertFromInternalUnits(lv.Elevation,
                                                  UnitTypeId.Meters)
        out.append((lv.Name, elev))
    return sorted(out, key=lambda x: x[1])


class SetupWindow(forms.WPFWindow):

    def __init__(self, settings):
        forms.WPFWindow.__init__(
            self, os.path.join(os.path.dirname(__file__), "ui.xaml"))
        self.s = settings
        self.saved = False
        self._texts()
        self._fill()

    # -- text in the current language
    def _texts(self):
        self.Title = t("setup.title")
        self.save_b.Content = t("btn.save")
        self.cancel_b.Content = t("btn.cancel")
        self.tab_scope.Header = t("setup.tab_scope")
        self.tab_levels.Header = t("setup.tab_levels")
        self.tab_lod.Header = t("setup.tab_lod")
        self.tab_codes.Header = t("setup.tab_codes")
        self.scope_intro.Text = t("setup.scope_intro")
        self.scope_other.Text = t("setup.scope_other")
        for sc in groups.SCOPES:
            getattr(self, "sc_" + sc).Content = t("scope." + sc)
            getattr(self, "sc_" + sc + "_d").Text = t("scope." + sc + ".d")
        self.building_l.Text = t("setup.building")
        self.ground_l.Text = t("setup.ground")
        self.suggest_b.Content = t("setup.suggest")
        self.levels_help.Text = t("setup.levels_help")
        cols = self.levels_dg.Columns
        cols[0].Header = t("setup.col_level")
        cols[1].Header = t("setup.col_elev")
        cols[2].Header = t("setup.col_code")
        self.roomnum_l.Text = t("setup.roomnum")
        self.doorroom_l.Text = t("setup.doorroom")
        self.lod_help.Text = t("setup.lod_help")
        self.lod_default_l.Text = t("setup.lod_default")
        self.lod_all_b.Content = t("setup.lod_all")
        self.lod_dg.Columns[0].Header = t("setup.col_group")
        self.lod_dg.Columns[1].Header = "LOD"
        self.tn_el_l.Text = t("setup.tn_elements")
        self.tn_sp_l.Text = t("setup.tn_spaces")
        self.pad_type_l.Text = t("setup.pad_type")
        self.pad_single_l.Text = t("setup.pad_single")
        self.mlnum_l.Text = t("setup.mlnum")
        self.write_topnode_cb.Content = t("setup.write_topnode")
        self.write_cls_cb.Content = t("setup.write_cls")
        self.cls_tn_cb.Content = t("setup.cls_tn")
        self.copy_inst_cb.Content = t("setup.copy_inst")
        self.copy_inst_d.Text = t("setup.copy_inst_d")
        self.ifc_h.Text = t("setup.ifc_h")
        self.ifc_edition_l.Text = t("setup.ifc_edition")
        self.ifc_date_l.Text = t("setup.ifc_date")
        self.ifc_loc_l.Text = t("setup.ifc_loc")
        self.ifc_d.Text = t("setup.ifc_d")

    # -- current settings into the controls
    def _fill(self):
        s = self.s
        for sc in groups.SCOPES:
            getattr(self, "sc_" + sc).IsChecked = sc in s["scopes"]
        self.building_tb.Text = str(s["building"])
        self.lvls = project_levels()
        names = [n for n, _ in self.lvls]
        self.ground_cb.ItemsSource = names
        if s["ground_level"] in names:
            self.ground_cb.SelectedItem = s["ground_level"]
        else:
            suggested = levels_mod.suggest_level_codes(self.lvls)
            for n in names:
                if suggested.get(n) == "01":
                    self.ground_cb.SelectedItem = n
        codes = dict(s["levels"])
        if not any(codes.get(n) for n in names):
            codes = levels_mod.suggest_level_codes(
                self.lvls, self.ground_cb.SelectedItem)
        self.level_rows = [LevelRow(n, e, codes.get(n)) for n, e in self.lvls]
        self.levels_dg.ItemsSource = self.level_rows
        self._combo(self.roomnum_cb, ROOM_MODES, "setup.roomnum.",
                    s["room_number_mode"])
        self._combo(self.doorroom_cb, DOOR_ROOMS, "setup.doorroom.",
                    s["door_room"])
        self.lod_default_cb.ItemsSource = LOD_OPTIONS
        self.lod_default_cb.SelectedItem = str(s["lod_default"])
        self.lod_rows = [LodRow(g, smod.lod_for(s, g))
                         for g in groups.GROUP_IDS]
        self.lod_dg.ItemsSource = self.lod_rows
        self._combo(self.tn_el_cb, list(formats.TOPNODES), "topnode.",
                    s["topnode_elements"])
        self._combo(self.tn_sp_cb, list(formats.TOPNODES), "topnode.",
                    s["topnode_spaces"])
        self.pad_type_cb.ItemsSource = PADS
        self.pad_type_cb.SelectedItem = str(s["type_pad"])
        self.pad_single_cb.ItemsSource = PADS
        self.pad_single_cb.SelectedItem = str(s["single_pad"])
        self._combo(self.mlnum_cb, ML_NUMBERS, "setup.mlnum.",
                    s["ml_number"])
        self.write_topnode_cb.IsChecked = s["write_topnode"]
        self.write_cls_cb.IsChecked = s["write_classification"]
        self.cls_tn_cb.IsChecked = s["classification_desc"]
        self.copy_inst_cb.IsChecked = s["copy_to_instance"]
        self.ifc_edition_tb.Text = s["ifc"]["edition"]
        self.ifc_date_tb.Text = s["ifc"]["edition_date"]
        self.ifc_loc_tb.Text = s["ifc"]["location"]

    def _combo(self, cb, keys, prefix, current):
        cb.ItemsSource = [("[%s] " % k if prefix == "topnode." else "")
                          + t(prefix + k) for k in keys]
        cb.Tag = keys
        if current in keys:
            cb.SelectedIndex = keys.index(current)

    @staticmethod
    def _picked(cb):
        i = cb.SelectedIndex
        return cb.Tag[i] if i >= 0 else None

    # -- events
    def suggest_click(self, sender, args):
        codes = levels_mod.suggest_level_codes(
            self.lvls, self.ground_cb.SelectedItem)
        for row in self.level_rows:
            row.code = codes.get(row.name, "")
        self.levels_dg.Items.Refresh()

    def lod_all_click(self, sender, args):
        for row in self.lod_rows:
            row.lod = self.lod_default_cb.SelectedItem
        self.lod_dg.Items.Refresh()

    def save_click(self, sender, args):
        s = dict(self.s)
        s["scopes"] = [sc for sc in groups.SCOPES
                       if getattr(self, "sc_" + sc).IsChecked]
        try:
            s["building"] = int(self.building_tb.Text.strip())
        except ValueError:
            s["building"] = self.building_tb.Text
        s["ground_level"] = self.ground_cb.SelectedItem
        s["levels"] = dict((r.name, r.code) for r in self.level_rows
                           if r.code)
        s["room_number_mode"] = self._picked(self.roomnum_cb)
        s["door_room"] = self._picked(self.doorroom_cb)
        s["lod_default"] = int(self.lod_default_cb.SelectedItem)
        s["lod"] = dict((r.gid, int(r.lod)) for r in self.lod_rows
                        if int(r.lod) != s["lod_default"])
        s["topnode_elements"] = self._picked(self.tn_el_cb)
        s["topnode_spaces"] = self._picked(self.tn_sp_cb)
        s["type_pad"] = int(self.pad_type_cb.SelectedItem)
        s["single_pad"] = int(self.pad_single_cb.SelectedItem)
        s["ml_number"] = self._picked(self.mlnum_cb)
        s["write_topnode"] = bool(self.write_topnode_cb.IsChecked)
        s["write_classification"] = bool(self.write_cls_cb.IsChecked)
        s["classification_desc"] = bool(self.cls_tn_cb.IsChecked)
        s["copy_to_instance"] = bool(self.copy_inst_cb.IsChecked)
        ifc = dict(self.s["ifc"])
        ifc["edition"] = self.ifc_edition_tb.Text.strip()
        ifc["edition_date"] = self.ifc_date_tb.Text.strip()
        ifc["location"] = self.ifc_loc_tb.Text.strip()
        s["ifc"] = ifc

        problems = smod.validate(s)
        if not s["scopes"]:
            problems.insert(0, ("set.no_scope", {}))
        if problems:
            forms.alert("\n".join(t(k, **p) for k, p in problems),
                        title=t("setup.title"))
            return
        self.s = s
        self.saved = True
        self.Close()


settings = storage.load_settings(doc)
win = SetupWindow(settings)
win.ShowDialog()
if win.saved:
    with ui.Tx(doc, "tx.setup"):
        storage.save_settings(doc, win.s)
    missing = [n for n, _ in win.lvls if n not in win.s["levels"]]
    if missing:
        ui.alert("setup.saved_missing_levels", names=", ".join(missing))
    else:
        ui.alert("setup.saved")
