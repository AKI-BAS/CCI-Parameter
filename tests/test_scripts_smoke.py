# -*- coding: utf-8 -*-
"""Runs the Revit button scripts end to end on a fake model."""
import os
import runpy
import types
import sys

import pytest

HERE = os.path.dirname(__file__)
SRC = os.path.join(HERE, "..", "src")
sys.path.insert(0, os.path.join(SRC, "lib"))
sys.path.insert(0, HERE)

import fake_revit as fr  # noqa: E402  (installs the fake modules)
from cci import formats, i18n  # noqa: E402

TYPE_KEYS = ["class_t", "topnode_t", "type_id_t", "classification_t"]
INST_KEYS = ["class", "topnode", "type_id", "ml_type_id", "single_id",
             "location_at_id", "classification"]


def cci(keys):
    return dict((formats.PARAM[k], "") for k in keys)


def run(button):
    path = os.path.join(SRC, "buttons", button, "script.py")
    try:
        runpy.run_path(path, run_name="__main__")
    except SystemExit:
        pass


@pytest.fixture()
def model(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    i18n.load(os.path.join(SRC, "lang", "en.json"))
    fr.Schema._one = None
    fr.STATE["alerts"] = []
    lvl1 = fr.Level("Hæð 1", 0.0)
    lvl0 = fr.Level("Kjallari", -10.0)
    room = fr.Element("OST_Rooms", "Stofa", dict(
        cci(["class", "topnode", "ml_location_id", "classification"]),
        Number="101", Name="Stofa"), level=lvl1,
        location=fr.LocationPoint())
    door_t = fr.Element("OST_Doors", "900x2100", cci(TYPE_KEYS),
                        family="Hurð")
    door_t.is_type = True
    doors = []
    for _ in range(2):
        d = fr.FamilyInstance("OST_Doors", "", cci(INST_KEYS), etype=door_t,
                              location=fr.LocationPoint())
        d.to_room = room
        doors.append(d)
    wall_t = fr.Element("OST_Walls", "Útveggur 300", cci(TYPE_KEYS),
                        family="Basic Wall")
    wall_t.is_type = True
    wall = fr.Wall("OST_Walls", "", cci(INST_KEYS), etype=wall_t)
    room2 = fr.Element("OST_Rooms", "Rými X", dict(
        cci(["class", "topnode", "ml_location_id", "classification"]),
        Number="102", Name="Rými X"), level=lvl1,
        location=fr.LocationPoint())
    generic_t = fr.Element("OST_GenericModel", "Kassi", {}, family="X")
    generic_t.is_type = True
    generic = fr.FamilyInstance("OST_GenericModel", "", {}, etype=generic_t)
    doc = fr.Doc([lvl1, lvl0, room, room2, door_t, wall_t, generic_t, generic,
                  wall] + doors)
    fr.STATE["doc"] = doc

    from cci.revit import storage
    from cci import settings
    s = settings.merged({
        "scopes": ["coordination", "operations", "product_id",
                   "location_id"],
        "levels": {"Hæð 1": "01", "Kjallari": "K1"}})
    storage.save_settings(doc, s)
    return dict(doc=doc, room=room, room2=room2, door_t=door_t,
                doors=doors, wall_t=wall_t, wall=wall,
                appdata=str(tmp_path / "appdata"))


def val(e, key):
    return e.LookupParameter(formats.PARAM[key]).AsString()


def test_full_workflow(model):
    run("classify")
    assert val(model["door_t"], "class_t") == "QQC"
    assert val(model["door_t"], "topnode_t") == "[L]"
    assert val(model["door_t"], "classification_t") == "QQC:Door"
    assert val(model["doors"][0], "class") == "QQC"       # copied
    assert val(model["wall_t"], "class_t") == "AD"
    assert val(model["room"], "class") == "AAB"            # "Stofa"
    assert val(model["room"], "topnode") == "[B]"
    assert val(model["room2"], "class") == ""              # no rule

    run("number")
    assert val(model["door_t"], "type_id_t") == "%QQC001"
    assert val(model["doors"][1], "type_id") == "%QQC001"
    assert val(model["doors"][0], "ml_type_id") == "§B.AD.QQC001"
    singles = sorted(val(d, "single_id") for d in model["doors"])
    assert singles == ["#QQC001", "#QQC002"]
    assert val(model["wall_t"], "type_id_t") == "%AD001"
    assert val(model["wall"], "single_id") == "#AD001"
    assert val(model["wall"], "ml_type_id") == ""          # AD is 2 letters

    # stable on a second run, and after hand edits elsewhere
    run("number")
    assert sorted(val(d, "single_id") for d in model["doors"]) == singles

    # a hand-set instance override survives a class change on the type
    model["doors"][0].LookupParameter("CCIClassCode").Set("QQB")
    run("classify")
    assert val(model["doors"][0], "class") == "QQB"

    run("locations")
    assert val(model["room"], "ml_location_id") == "B01.01.101"
    assert val(model["doors"][0], "location_at_id") == "+B01.01.101"

    run("check")
    out = fr.STATE["output"].lines
    text = "\n".join(x for x in out if isinstance(x, str))
    assert "errors" in text
    tables = [x for x in out if isinstance(x, tuple)]
    findings = " ".join(row[2] for _, _, rows in tables for row in rows)
    assert "CCIClassCode is empty" in findings            # room2
    assert "CCI table: Molio CCI 2020-05-26 R1" in text
    assert "doesn't match class QQB" in findings          # door 0 override


def test_new_element_gets_next_number(model):
    run("classify")
    run("number")
    d = fr.FamilyInstance("OST_Doors", "", cci(INST_KEYS),
                          etype=model["door_t"])
    model["doc"].elements.append(d)
    run("classify")
    run("number")
    assert val(d, "single_id") == "#QQC003"
    assert val(d, "type_id") == "%QQC001"


def test_setup_window_round_trip(model):
    """Every control is filled from the stored settings and read back on
    Save: nothing may be lost or changed on the way."""
    from cci.revit import storage
    before = storage.load_settings(model["doc"])
    run("setup")
    assert "Settings saved in the project." in fr.STATE["alerts"]
    after = storage.load_settings(model["doc"])
    # the 1st floor was not set, so the window picked the level at 0
    assert after.pop("ground_level") == "Hæð 1"
    before.pop("ground_level")
    assert after == before


def test_ifc_and_number_scope(model, monkeypatch, tmp_path):
    target = str(tmp_path / "CCI_in_Revit_to_IFC.txt")
    monkeypatch.setattr(fr.forms, "save_file", lambda **k: target)
    run("ifc")
    with open(target, encoding="utf-8") as f:
        assert "CCI_Administrative" in f.read()


def test_studio_rule_wins(model):
    """A rule in the studio data folder beats the shipped defaults."""
    from cci.revit import util
    st = util.store()
    st.add_rule({"id": "studio:test", "category": ["OST_Doors"],
                 "match": {"family": "Hurð", "type": "900x2100"},
                 "class": "QQE"})
    assert st.user.startswith(model["appdata"])
    run("classify")
    assert val(model["door_t"], "class_t") == "QQE"


# Molio's original spreadsheets (P150a-d), if you have them locally.
# Tests that need them are skipped otherwise.
MOLIO = os.environ.get("CCI_MOLIO_DIR", "")


def _choose(monkeypatch, label):
    monkeypatch.setattr(fr.forms.CommandSwitchWindow, "show",
                        staticmethod(lambda options, **k: label))


def test_table_update_from_json_and_switch(model, monkeypatch, tmp_path):
    from cci import compat
    from cci.revit import util
    shipped = util.store().load_table_data()
    new = dict(shipped, id="test-2026", name="Test 2026")
    new["domains"] = dict(shipped["domains"])
    new["domains"]["L"] = dict(shipped["domains"]["L"])
    del new["domains"]["L"]["QQC"]
    path = str(tmp_path / "new.json")
    compat.save_json(path, new)
    run("classify")                       # doors now QQC in the model
    _choose(monkeypatch, "Update from files")
    monkeypatch.setattr(fr.forms, "pick_file", lambda **k: [path])
    run("table")
    assert util.store().active_id() == "test-2026"
    lines = [x for x in fr.STATE["output"].lines if isinstance(x, str)]
    assert any("1 removed" in x for x in lines)
    assert any("not in the new table (1)" in x for x in lines)
    # Check now reports the door code as unknown
    run("check")
    tables = [x for x in fr.STATE["output"].lines if isinstance(x, tuple)]
    findings = " ".join(row[2] for _, _, rows in tables for row in rows)
    assert 'Class "QQC" is not in the CCI table' in findings
    # and switching back works
    _choose(monkeypatch, "Switch version")
    monkeypatch.setattr(fr.forms.SelectFromList, "show", staticmethod(
        lambda labels, **k: [x for x in labels if "molio" in x][0]))
    run("table")
    assert util.store().active_id() == "molio-cci-20200526-R1"


@pytest.mark.skipif(not os.path.isdir(MOLIO), reason="Molio files not here")
def test_table_update_from_link(model, monkeypatch):
    """A 'link' can be paths on a shared drive; several in one go."""
    from cci.revit import util
    links = " ".join(os.path.join(MOLIO, f) for f in sorted(os.listdir(MOLIO)))
    _choose(monkeypatch, "Update from link")
    monkeypatch.setattr(fr.forms, "ask_for_string", lambda **k: links)
    run("table")
    st = util.store()
    assert st.config()["table_link"] == links
    assert os.path.exists(os.path.join(st.user, "tables",
                                       "molio-cci-20200526-R1.json"))
    assert st.active_id() == "molio-cci-20200526-R1"


def test_names_export_import(model, monkeypatch, tmp_path):
    from cci.revit import util
    csv = str(tmp_path / "names.csv")
    _choose(monkeypatch, "Export Icelandic names (CSV)")
    monkeypatch.setattr(fr.forms, "save_file", lambda **k: csv)
    run("table")
    with open(csv, encoding="utf-8-sig") as f:
        text = f.read()
    assert "L;QQC;3;Door;Dør;Hurð;bim_island" in text
    assert "L;QQA;3;Window;Vindue;Gluggi;draft" in text
    edited = text.replace("L;QQA;3;Window;Vindue;Gluggi;draft",
                          "L;QQA;3;Window;Vindue;Gluggi;reviewed")
    edited = edited.replace("L;BAA;3;Voltage transformer;"
                            "Spændingstransformer;;missing",
                            "L;BAA;3;Voltage transformer;"
                            "Spændingstransformer;Spennuspennir;missing")
    with open(csv, "w", encoding="utf-8-sig") as f:
        f.write(edited)
    _choose(monkeypatch, "Import Icelandic names (CSV)")
    monkeypatch.setattr(fr.forms, "pick_file", lambda **k: csv)
    run("table")
    table = util.store().load_table()
    assert table.name("BAA", "is", "[L]") == "Spennuspennir"
    assert table.name_status("QQA", "[L]") == "reviewed"


def test_old_coding_is_replaced(model, monkeypatch):
    """A model with old coding: wrong code on the type, an old code on a
    single element and an old CCIClassification format. 'Replace old
    coding' + 'overwrite single elements' cleans all of it."""
    door_t, d0 = model["door_t"], model["doors"][0]
    door_t.LookupParameter("CCIClassCode[Type]").Set("QQX")      # not in table
    door_t.LookupParameter("CCIClassification[Type]").Set(
        "[CCI][L]QQX:Old door")
    d0.LookupParameter("CCIClassCode").Set("QQB")                # on element

    def write_click(self, sender, args):
        self.replace_click(None, None)
        self.reset_inst_cb.IsChecked = True
        self.reset_instances = True
        self.ok = True

    path = os.path.join(SRC, "buttons", "classify", "script.py")
    src = open(path, encoding="utf-8").read()
    src = src.replace("    def write_click(self, sender, args):",
                      "    def _orig_write_click(self, sender, args):")
    src = src.replace("class ClassifyWindow(forms.WPFWindow):",
                      "class ClassifyWindow(forms.WPFWindow):\n"
                      "    write_click = _TEST_WRITE_CLICK")
    code = compile(src, path, "exec")
    try:
        exec(code, {"__name__": "__main__", "__file__": path,
                    "_TEST_WRITE_CLICK": write_click})
    except SystemExit:
        pass
    assert val(door_t, "class_t") == "QQC"
    assert val(door_t, "classification_t") == "QQC:Door"
    assert val(d0, "class") == "QQC"                  # element override reset
    assert any("rows changed" in a for a in fr.STATE["alerts"])


def test_elements_without_a_type(model):
    """Shaft openings have no type: classified and numbered on the
    element itself, and Check doesn't ask them for a type ID."""
    shaft = fr.Element("OST_ShaftOpening", "Shaft", cci(INST_KEYS))
    shaft2 = fr.Element("OST_ShaftOpening", "Shaft", cci(INST_KEYS))
    model["doc"].elements += [shaft, shaft2]
    from cci.revit import storage
    s = storage.load_settings(model["doc"])
    s["lod"]["openings"] = 400
    storage.save_settings(model["doc"], s)
    run("classify")
    code = val(shaft, "class")
    assert code and code == val(shaft2, "class")
    run("number")
    ids = sorted([val(shaft, "single_id"), val(shaft2, "single_id")])
    assert ids == ["#%s001" % code, "#%s002" % code]
    run("check")
    tables = [x for x in fr.STATE["output"].lines if isinstance(x, tuple)]
    findings = " ".join(" ".join("%s" % c for c in row)
                        for _, _, rows in tables for row in rows)
    shaft_rows = [row for _, _, rows in tables for row in rows
                  if "Shaft" in " ".join("%s" % c for c in row)]
    assert not any("CCITypeID" in "%s" % row for row in shaft_rows)


def test_selection_without_elements_uses_whole_model(model):
    """A selected view, tag or line has nothing to classify: Classify
    falls back to the whole model instead of saying there is nothing."""
    fr.STATE["selection"] = [fr.Element("OST_Lines", "Detail line", {})]
    try:
        run("classify")
    finally:
        fr.STATE["selection"] = []
    assert val(model["door_t"], "class_t") == "QQC"


def test_closing_with_changes_asks_first(model, monkeypatch):
    """Escape/Cancel/X on Classify: no changes closes, changes ask."""
    import runpy
    asked = []
    seen = {}

    def show(self):
        args = types.SimpleNamespace(Cancel=False)
        self.on_closing(None, args)            # nothing changed
        seen["clean"] = args.Cancel
        self.rows[0].code = "QQZ"
        fr.STATE["confirm"] = False            # "No, keep the window"
        self.on_closing(None, args)
        seen["kept"] = args.Cancel

    monkeypatch.setattr(fr.WPFWindow, "ShowDialog", show)
    monkeypatch.setattr(fr.forms, "alert",
                        lambda msg, **k: asked.append(msg) or
                        fr.STATE["confirm"])
    run("classify")
    assert seen == {"clean": False, "kept": True}
    assert len(asked) == 1


def test_equipment_in_a_room_gets_its_location(model):
    """element.Room is an indexer in IronPython; get_Room(phase) is used."""
    sink_t = fr.Element("OST_PlumbingFixtures", "Vaskur", cci(TYPE_KEYS),
                        family="Vaskur")
    sink_t.is_type = True
    sink = fr.FamilyInstance("OST_PlumbingFixtures", "", cci(INST_KEYS),
                             etype=sink_t, location=fr.LocationPoint())
    sink.room = model["room"]
    model["doc"].elements += [sink_t, sink]
    run("locations")
    assert val(sink, "location_at_id") == "+B01.01.101"


def test_room_numbers_with_storey_get_a_hint(model):
    model["room"].LookupParameter("Number").Set("01-03")
    run("locations")
    text = "\n".join(x for x in fr.STATE["output"].lines
                     if isinstance(x, str))
    assert "Last part of Number" in text
    from cci.revit import storage
    s = storage.load_settings(model["doc"])
    s["room_number_mode"] = "last_segment"
    storage.save_settings(model["doc"], s)
    run("locations")
    assert val(model["room"], "ml_location_id") == "B01.01.003"


def test_location_id_scope_also_numbers_rooms(model):
    from cci.revit import storage
    s = storage.load_settings(model["doc"])
    s["scopes"] = ["coordination", "location_id"]
    storage.save_settings(model["doc"], s)
    run("locations")
    assert val(model["room"], "ml_location_id") == "B01.01.101"
    assert val(model["doors"][0], "location_at_id") == "+B01.01.101"


def test_element_in_several_rooms_gets_the_lowest(model):
    """A column (no single room) between a room on 1st floor and one on
    the basement level gets the basement room's location."""
    from cci.revit import storage
    s = storage.load_settings(model["doc"])
    s["room_number_mode"] = "as_is"
    storage.save_settings(model["doc"], s)
    lvl0 = [e for e in model["doc"].elements
            if isinstance(e, fr.Level) and e.Name == "Kjallari"][0]
    low = fr.Element("OST_Rooms", "Geymsla", dict(
        cci(["class", "topnode", "ml_location_id", "classification"]),
        Number="7", Name="Geymsla"), level=lvl0, location=fr.LocationPoint())
    col_t = fr.Element("OST_StructuralColumns", "Súla", cci(TYPE_KEYS))
    col_t.is_type = True
    col = fr.Element("OST_StructuralColumns", "", cci(INST_KEYS),
                     etype=col_t)
    col.bbox = fr.BoundingBox((0, 0, -10), (1, 1, 10))
    model["doc"].elements += [low, col_t, col]
    model["doc"].room_at = lambda p: low if p[2] < 0 else model["room"]
    run("locations")
    assert val(low, "ml_location_id") == "B01.K1.007"
    assert val(col, "location_at_id") == "+B01.K1.007"
