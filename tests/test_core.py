# -*- coding: utf-8 -*-
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src",
                                "lib"))

from cci import checker, formats, groups, ifcmap, levels, numbering  # noqa
from cci import rules, settings  # noqa


# ------------------------------------------------- examples from the guide

@pytest.mark.parametrize("value", [
    "%QQC001", "%QQC01.001", "%AD001", "%QMB01.301", "[L]%QQC002"])
def test_type_id_examples_valid(value):
    assert formats.check_type_id(value) is None


@pytest.mark.parametrize("value", [
    "§B.AD.QQC001", "§B.AD.QQC01.001", "§K.HH.UAC010"])
def test_ml_type_id_examples_valid(value):
    assert formats.check_ml_type_id(value) is None


@pytest.mark.parametrize("value", [
    "=H01.HD02.EGC001", "=J01.HF01.JG01.QNA021"])
def test_functional_examples_valid(value):
    assert formats.check_functional_id(value) is None


@pytest.mark.parametrize("value", ["#QQC001", "#AD001", "#QMB301",
                                   "#UAC593"])
def test_single_examples_valid(value):
    assert formats.check_single_id(value) is None


@pytest.mark.parametrize("value", ["B01.01.001", "B03.K1.051",
                                   "B01.M3.001", "B2.K2.010"])
def test_location_examples(value):
    # B2.K2.010 is in the summary table but has a 1-digit building; the
    # detailed section says xx (two digits), so it is flagged.
    expect_ok = value != "B2.K2.010"
    assert (formats.check_location_id(value) is None) == expect_ok


def test_location_plus_rules():
    assert formats.check_location_id("+B01.01.001") == "fmt.location_plus"
    assert formats.check_location_at_id("+B01.01.001") is None
    assert formats.check_location_at_id("B01.01.001") == \
        "fmt.location_at_prefix"


def test_builders():
    assert formats.type_id("qqc", 1) == "%QQC001"
    assert formats.type_id("QQC", 1, sub=1) == "%QQC01.001"
    assert formats.type_id("QQC", 2, with_topnode="L") == "[L]%QQC002"
    assert formats.ml_type_id("B", "AD", "QQC", 1) == "§B.AD.QQC001"
    assert formats.single_id("UAC", 593) == "#UAC593"
    assert formats.location_id(1, "01", 1) == "B01.01.001"
    assert formats.location_at_id(3, "K1", 51) == "+B03.K1.051"
    assert formats.classification("AD") == "AD"
    assert formats.classification("ad", "Wall construction") == \
        "AD:Wall construction"
    assert formats.classification("UAC", "a:b") == "UAC:a b"
    assert formats.code_of_classification("[CCI][L]AD:Wall construction") \
        == "AD"
    assert formats.classification_prefix("[L]AD") == "L"
    assert formats.classification_prefix("AD:x") is None
    assert formats.check_classification("[CCI][L]AD:Wall") is None
    assert formats.check_classification("ad") == "fmt.classification"
    with pytest.raises(ValueError):
        formats.type_id("QQ1", 1)
    with pytest.raises(ValueError):
        formats.topnode("X")


def test_bad_values():
    assert formats.check_class("QQCC") == "fmt.class_code"
    assert formats.check_class("qqc") == "fmt.class_code"
    assert formats.check_topnode("[X]") == "fmt.topnode"
    assert formats.check_topnode("L") == "fmt.topnode"
    assert formats.check_type_id("QQC001") == "fmt.type_id"
    assert formats.check_ml_type_id("§BB.AD.QQC001") == "fmt.ml_type_id"


def test_has_subtype():
    assert formats.has_subtype("%QQC01.001", "QQC")
    assert formats.has_subtype("§B.AD.QQC01.001", "QQC")
    assert not formats.has_subtype("%QQC001", "QQC")
    assert not formats.has_subtype("%QQC01.001", "QQB")


def test_class_of_id():
    assert formats.class_of_id("%QQC001") == "QQC"
    assert formats.class_of_id("[L]%QQC01.001") == "QQC"
    assert formats.class_of_id("#UAC593") == "UAC"
    assert formats.class_of_id("§K.HH.UAC010") == "UAC"
    assert formats.class_of_id("=H01.HD02.EGC001") == "EGC"
    assert formats.number_of_id("%QQC012") == 12


# --------------------------------------------------------------- levels

def test_suggest_level_codes():
    lv = [("Kjallari", -3.0), ("Hæð 1", 0.0), ("Hæð 2", 3.2),
          ("Kjallari 2", -6.0), ("Þak", 6.4)]
    codes = levels.suggest_level_codes(lv)
    assert codes == {"Kjallari 2": "K2", "Kjallari": "K1", "Hæð 1": "01",
                     "Hæð 2": "02", "Þak": "03"}
    codes = levels.suggest_level_codes(lv, ground_name="Hæð 2")
    assert codes["Hæð 2"] == "01" and codes["Hæð 1"] == "K1"


def test_room_number():
    assert levels.room_number("7") == "007"
    assert levels.room_number("101") == "101"
    assert levels.room_number("1.101") is None
    assert levels.room_number("2.101", "last_segment") == "101"
    assert levels.room_number("01-03", "last_segment") == "003"
    assert levels.room_number("01-03") is None
    assert levels.room_number("1001") is None
    assert levels.room_number("") is None
    assert levels.room_number("A12") is None


def test_auto_room_numbers():
    out = levels.auto_room_numbers([("a", "01", 3), ("b", "01", 1),
                                    ("c", "02", 1)])
    assert out == {"b": "001", "a": "002", "c": "001"}


def test_auto_room_numbers_are_stable_and_natural():
    rooms = [("r2", "01", ("2", 5)), ("r10", "01", ("10", 1)),
             ("r1", "01", ("1", 9))]
    first = levels.auto_room_numbers(rooms)
    assert first == {"r1": "001", "r2": "002", "r10": "003"}
    # a new room "1a" sorts between 1 and 2 but must not renumber others
    rooms.append(("r1a", "01", ("1a", 3)))
    again = levels.auto_room_numbers(rooms, existing=first)
    assert again == dict(first, r1a="004")
    # two rooms claiming the same number: the first in order keeps it
    dup = levels.auto_room_numbers(rooms[:2], existing={"r2": "001",
                                                        "r10": "001"})
    assert sorted(dup.values()) == ["001", "002"] and dup["r2"] == "001"
    assert formats.parse_location("+B01.K1.007") == ("01", "K1", "007")
    assert formats.parse_location("B1.01.7") is None


# ------------------------------------------------------------ numbering

def test_registry_prime_reserves_existing_ids():
    r = numbering.Registry()
    s = numbering.series("single", "QQC")
    # element b already has #QQC001 in the model; a has nothing
    assert r.prime(s, "b", "#QQC001")
    assert not r.prime(s, "c", "#QQB004")       # other class: not taken
    assert r.number_for(s, "a") == 2           # does not steal 1
    assert r.number_for(s, "b", "#QQC001") == 1
    assert not r.prime(s, "b", "#QQC009")      # already known: unchanged
    assert r.number_for(s, "b") == 1


def test_registry_is_stable():
    r = numbering.Registry()
    s = numbering.series("type", "QQC")
    assert r.allocate(s, "a") == 1
    assert r.allocate(s, "b") == 2
    assert r.allocate(s, "a") == 1
    r.forget_missing(s, ["b"])
    assert r.allocate(s, "c") == 3   # 1 is retired, not reused
    r2 = numbering.Registry(r.to_data())
    assert r2.allocate(s, "b") == 2


def test_registry_adopt_and_move():
    r = numbering.Registry()
    s = numbering.series("single", "QQC")
    assert r.adopt(s, "x", 7)
    assert not r.adopt(s, "y", 7)    # duplicate in model
    assert r.allocate(s, "y") == 8
    assert r.move(s, numbering.series("single", "QQB"), "x") == 1


def test_number_for():
    r = numbering.Registry()
    s = numbering.series("type", "QQC")
    assert r.number_for(s, "a", "%QQC005") == 5        # adopted
    assert r.number_for(s, "b", "%QQC005") == 6        # taken -> next
    assert r.number_for(s, "c", "%QQB002") == 7        # other class
    assert r.number_for(s, "a") == 5                   # stable
    s2 = numbering.series("type", "QQB")
    assert r.number_for(s2, "a") == 1                  # class changed
    assert r.get(s, "a") is None
    assert r.number_for(s, "d") == 8                   # 5 not reused
    rd = numbering.Registry(r.to_data())
    assert rd.get(s2, "a") == 1 and rd.parents == {}


def test_resolve_instance():
    ri = numbering.resolve_instance
    assert ri("", "", "QQC", True) == "QQC"            # fill empty
    assert ri("QQB", "QQB", "QQC", True) == "QQC"      # stale copy
    assert ri("XYZ", "QQB", "QQC", True) is None       # override kept
    assert ri("QQC", "QQB", "QQC", True) is None       # already right
    assert ri("QQB", "QQB", "QQC", False) == ""        # clear copy
    assert ri("", "", "QQC", False) is None


# ---------------------------------------------------------------- groups

def test_group_of():
    assert groups.group_of({"category": "OST_Walls"}) == "light_walls"
    assert groups.group_of({"category": "OST_Walls",
                            "structural": True}) == "concrete_walls"
    assert groups.group_of({"category": "OST_Walls",
                            "curtain": True}) == "curtain_walls"
    assert groups.group_of({"category": "OST_StructuralColumns",
                            "material": "Steel"}) == "steel_columns"
    assert groups.group_of({"category": "OST_Doors"}) == "doors"
    assert groups.group_of({"category": "OST_GenericModel"}) is None
    assert groups.kind_of("OST_PlumbingFixtures") == "system"
    assert groups.kind_of("OST_Rooms") == "space"


def test_required_fields_lod_gate():
    rf = groups.required_fields
    assert rf("element", "doors", 200, ["coordination"]) == []
    assert rf("element", "doors", 300, ["coordination"]) == ["class",
                                                            "type_id"]
    assert rf("element", "openings", 300, ["coordination"]) == []
    assert rf("element", "openings", 400, ["coordination"]) == [
        "class", "type_id", "single_id"]
    assert "functional_id" not in rf("element", "doors", 300, ["systems"])
    assert "functional_id" in rf("system", "plumbing", 300, ["systems"])
    sp = rf("space", "spaces", 300, ["operations"])
    assert "ml_location_id" in sp and "ml_type_id" not in sp


# ----------------------------------------------------------------- rules

RULES = {"rules": [
    {"id": "door", "category": ["OST_Doors"], "class": "QQC", "u": "B",
     "vv": "AD", "verified": True},
    {"id": "fire_door", "category": ["OST_Doors"],
     "match": {"name_contains": ["eldvarnar"]}, "class": None},
    {"id": "ext_wall", "category": ["OST_Walls"],
     "match": {"params": {"Function": "Exterior"}}, "class": "AD"},
    {"id": "wall", "category": ["OST_Walls"], "class": "AD"},
]}


def test_rules():
    rs = rules.RuleSet(RULES)
    assert rs.problems == []
    r = rs.classify({"category": "OST_Doors", "family": "Hurð",
                     "type": "900"})
    assert (r.class_code, r.source, r.u, r.vv, r.topnode, r.verified) == \
        ("QQC", "category", "B", "AD", "L", True)
    r = rs.classify({"category": "OST_Doors", "type": "Eldvarnarhurð"})
    assert r.source == "pending" and r.class_code is None
    r = rs.classify({"category": "OST_Walls",
                     "params": {"Function": "Exterior"}})
    assert r.rule_id == "ext_wall"
    r = rs.classify({"category": "OST_Rooms"}, kind="space")
    assert r.source == "none" and r.topnode == "B"


def test_rule_problems():
    rs = rules.RuleSet({"rules": [{"id": "a", "class": "Q1"},
                                  {"id": "a", "topnode": "X"}]})
    keys = [p[0] for p in rs.problems]
    assert keys == ["rules.bad_class", "rules.duplicate_id",
                    "rules.bad_topnode"]


# --------------------------------------------------------------- checker

def _rec(**kw):
    rec = {"id": "1", "label": "x", "category": "OST_Doors",
           "kind": "element", "group": "doors",
           "bound": list(groups.PARAMS_BY_KIND["element"]),
           "values": {}, "type_uid": "t1"}
    rec.update(kw)
    return rec


def test_checker_missing_and_ok():
    s = settings.merged({"scopes": ["coordination"]})
    issues = checker.check([_rec()], s)
    assert sorted(i.key for i in issues) == ["chk.missing", "chk.missing"]
    ok = _rec(values={"class_t": "QQC", "type_id_t": "%QQC001",
                      "topnode_t": "[L]", "classification_t": "QQC:Door"})
    assert checker.check([ok], s) == []


def test_checker_lod200_needs_nothing():
    s = settings.merged({"scopes": ["coordination"], "lod_default": 200})
    assert checker.check([_rec()], s) == []


def test_checker_findings():
    s = settings.merged({"scopes": ["coordination", "product_id"]})
    from cci import importer, table as table_mod
    data = importer.empty_table()
    data["id"] = "t"
    data["domains"]["L"]["QQC"] = {"en": "Door"}
    table = table_mod.ClassTable(data)
    a = _rec(id="1", values={"class_t": "QQC", "type_id_t": "%QQB001",
                             "single_id": "#QQC001", "class": "QQX"})
    b = _rec(id="2", type_uid="t2",
             values={"class_t": "QQC", "type_id_t": "%QQB001",
                     "single_id": "#QQC001", "functional_id": "=H01"})
    keys = [i.key for i in checker.check([a, b], s, table)]
    assert "chk.unknown_class" in keys            # QQX on a
    assert "chk.override" in keys                 # class differs from type
    assert "chk.id_class_mismatch" in keys        # %QQB001 vs QQC
    assert keys.count("chk.duplicate") == 2       # #QQC001 twice
    assert "chk.duplicate_type_id" in keys        # same type id, 2 types
    assert "chk.not_applicable" in keys           # functional id on a door
    assert "chk.format" in keys                   # "=H01" is malformed


def test_checker_skips_what_cant_apply():
    s = settings.merged({"scopes": ["operations", "location_id"]})
    wall = _rec(category="OST_Walls", group="light_walls", has_point=False,
                values={"class_t": "AD", "topnode_t": "[L]",
                        "classification_t": "AD"})
    assert checker.check([wall], s) == []
    door = _rec(has_point=True, values={"class_t": "QQC", "topnode_t": "[L]"})
    keys = sorted(i.params["param"] for i in checker.check([door], s))
    assert keys == ["CCIMultiLevelTypeID", "CCISingleLevelLocationAtID"]


def test_checker_not_bound():
    s = settings.merged({"scopes": ["coordination"]})
    issues = checker.check([_rec(bound=[])], s)
    assert {i.key for i in issues} == {"chk.not_bound"}


def test_settings_validate():
    s = settings.merged({"building": 100, "levels": {"A": "1"},
                         "lod": {"doors": 350}})
    keys = [k for k, _ in settings.validate(s)]
    assert keys == ["set.building", "fmt.level_code", "set.lod"]
    assert settings.validate(settings.merged({})) == []


def test_ifc_file():
    text = ifcmap.pset_file()
    assert "PropertySet:\tCCI_Administrative\tI\tIfcRoot" in text
    assert "\tCCIClassCode\tText\tCCIClassCode[Type]" in text
    lines = text.splitlines()
    # instance line comes after the type line so it wins
    assert lines.index("\tCCIClassCode\tText\tCCIClassCode") > \
        lines.index("\tCCIClassCode\tText\tCCIClassCode[Type]")


def test_checker_classification_format():
    s = settings.merged({"scopes": ["coordination"]})
    base = {"class_t": "QQC", "type_id_t": "%QQC001", "topnode_t": "[L]"}
    keys = lambda v: [i.key for i in checker.check(  # noqa: E731
        [_rec(values=dict(base, classification_t=v))], s)]
    assert keys("QQC:Door") == []
    assert keys("[CCI][L]QQC:Door") == []        # Revit-style, other tool
    assert keys("[L]QQC") == ["chk.classification_topnode"]
    assert keys("QQA:Window") == ["chk.classification_mismatch"]


def test_checker_softer_outside_lod_groups_and_ifc_skip():
    s = settings.merged({"scopes": ["coordination"]})
    generic = _rec(category="OST_GenericModel", group=None)
    assert {i.severity for i in checker.check([generic], s)} == {"warning"}
    hidden = _rec(exported=False)
    assert checker.check([hidden], s) == []


def test_overview():
    recs = [_rec(id="1", type_uid="a", cat_name="Doors",
                 values={"class_t": "QQC"}),
            _rec(id="2", type_uid="a", cat_name="Doors",
                 values={"class_t": "QQC"}),
            _rec(id="3", type_uid="b", cat_name="Doors", values={})]
    assert checker.overview(recs) == [("Doors", "", "", 1, 1),
                                      ("Doors", "QQC", "", 1, 2)]


def test_is_leftover():
    assert formats.is_leftover("CCITypeID_Type")
    assert formats.is_leftover("CCITypeName_Type")
    assert formats.is_leftover("CCSClassCode_Type")
    assert not formats.is_leftover("CCITypeID[Type]")
    assert not formats.is_leftover("CCITopNode[Type]")      # case only
    assert not formats.is_leftover("CCIClassName[Type]")    # Molio extra
    assert not formats.is_leftover("CCIClassification")
    assert not formats.is_leftover("Auðkenni_Type")


def test_functional_id_examples_from_bim_island():
    for v in ("=H01.HD02.EGC001", "=J01.HF01.JG01.QNA021",
              "=H201.HD002.EPC001"):
        assert formats.check_functional_id(v) is None, v
    assert formats.check_functional_id("=H1.HD02.EGC001")


def test_lowest_room():
    assert levels.lowest_room([(3.0, "B01.02.001"), (0.0, "B01.01.010"),
                               (0.0, "B01.01.002"), (-3.0, None)]) \
        == "B01.01.002"
    assert levels.lowest_room([]) is None


def test_storey_of_number_and_four_digit_ids():
    assert levels.storey_of_number("02-37") == "02"
    assert levels.storey_of_number("1.105") == "01"
    assert levels.storey_of_number("K1-04") == "K1"
    assert levels.storey_of_number("0025") is None
    assert levels.storey_of_number("101") is None
    assert formats.check_type_id("%BF0007") is None
    assert formats.check_ml_type_id("§B.AD.QQC0001") is None
    assert formats.check_type_id("%BF00007")
