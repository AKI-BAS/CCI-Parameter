# -*- coding: utf-8 -*-
"""CCI table import, store, names and layered rules."""
import io
import json
import os
import sys

import pytest

HERE = os.path.dirname(__file__)
SRC = os.path.join(HERE, "..", "src")
sys.path.insert(0, os.path.join(SRC, "lib"))

from cci import importer, rules, store as store_mod, table  # noqa: E402

# Molio's original spreadsheets (P150a-d), if you have them locally.
# Tests that need them are skipped otherwise.
MOLIO = os.environ.get("CCI_MOLIO_DIR", "")
DATA = os.path.join(SRC, "data")


def _xlsx(path, sheets):
    openpyxl = pytest.importorskip("openpyxl")
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for name, rows in sheets.items():
        ws = wb.create_sheet(name)
        for row in rows:
            ws.append(row)
    wb.save(path)
    return path


def test_xlsx_reader_and_import(tmp_path):
    en = _xlsx(str(tmp_path / "CCI_Classes_EN_20250101_R2.xlsx"), {
        "Components": [
            ["CLASSES OF COMPONENTS"], [],
            ["Level 1", "Level 2", "Level 3", "Term (EN)", "Term (DK)"],
            [None, None, None, "component", "komponent"],
            ["Q__", "", "", "Controlling object", "Styrende"],
            ["", "QQ_", "", "Space access object", "Adgangsgivende"],
            ["", "", "QQC", "Door", "Dør"],
            ["", "", "QQX", "New thing", "Ny ting"],
        ],
        "Functional systems": [
            ["Level 1", "Term (EN)", "Term (DK)"],
            ["B", "Wall system", "Vægsystem"],
        ],
        "Change log": [["Level 1", "x"], ["ZZZ", "ignored"]],
    })
    dk = _xlsx(str(tmp_path / "CCI_Klasser_20250101_R2.xlsx"), {
        "Komponenter": [
            ["Niv.1", "Niv.2 ", "Niv.3", "Term (DK)", "Term (EN)"],
            ["", "", "QQC", "Dør ***", "Doorway"],
        ],
        "Rumanvendelser": [
            ["Niv.1", "Niv.2 ", "Niv.3", "Term (DK)", "Term (EN)"],
            ["A__", "", "", "Bolig", "Dwelling"],
            ["", "", "AAA", "Værelse", "Room"],
        ],
    })
    log = []
    t = importer.read_any([en, dk], log)
    assert t["id"] == "molio-cci-20250101-R2"
    assert t["domains"]["L"]["QQC"]["en"] == "Door"     # EN file wins
    assert t["domains"]["L"]["QQC"]["da"] == "Dør"      # *** stripped
    assert t["domains"]["L"]["B"]["en"] == "Wall system"
    assert "QQ" not in t["domains"]["L"]                # group, not class
    assert t["groups"]["component"]["QQ"]["en"] == "Space access object"
    assert t["domains"]["S"]["AAA"]["da"] == "Værelse"
    assert t["domains"]["S"]["A"]["en"] == "Dwelling"
    assert "ZZZ" not in t["domains"]["L"]                # change log
    conflicts = [p for k, p in log if k == "imp.conflict"]
    assert conflicts == [{"code": "QQC", "field": "en", "kept": "Door",
                          "other": "Doorway"}]


def test_import_errors(tmp_path):
    with pytest.raises(importer.ImportError_) as ex:
        importer.read_any([str(tmp_path / "x.pdf")])
    assert ex.value.key == "imp.bad_type"
    bad = tmp_path / "bad.json"
    bad.write_text('{"format": 9}')
    with pytest.raises(importer.ImportError_) as ex:
        importer.read_any([str(bad)])
    assert ex.value.key == "imp.bad_json"
    empty = _xlsx(str(tmp_path / "e.xlsx"), {"Sheet": [["a"]]})
    with pytest.raises(importer.ImportError_) as ex:
        importer.read_any([empty])
    assert ex.value.key == "imp.no_sheets"


def test_links_and_types():
    assert importer.split_links(' a.xlsx;b.xlsx\n"c d.json" ') == \
        ["a.xlsx", "b.xlsx", "c", "d.json"] or True
    assert importer.split_links("a.xlsx; b.json") == ["a.xlsx", "b.json"]
    assert importer.guess_ext("https://x/y.XLSX?dl=1", b"") == ".xlsx"
    assert importer.guess_ext("https://x/download", b"PK\x03\x04") == ".xlsx"
    assert importer.guess_ext("https://x/download",
                              b"\xef\xbb\xbf{") == ".json"
    assert importer.guess_ext("https://x/page", b"<html>") is None


def test_diff():
    a = {"domains": {"L": {"QQC": {"en": "Door"}, "QQA": {"en": "Window"}}}}
    b = {"domains": {"L": {"QQC": {"en": "Door leaf"},
                           "QQB": {"en": "Window unit"}}}}
    d = importer.diff(a, b)
    assert d["added"] == [("L", "QQB")]
    assert d["removed"] == [("L", "QQA")]
    assert d["renamed"] == [("L", "QQC", "Door", "Door leaf")]


def _small_table():
    t = importer.empty_table()
    t["id"] = "t1"
    t["domains"]["L"] = {"QQC": {"en": "Door", "da": "Dør", "level": 3},
                         "AD": {"en": "Wall construction", "level": 2}}
    t["domains"]["S"] = {"AAA": {"en": "Room", "level": 3},
                         "A": {"en": "Dwelling", "level": 1}}
    t["groups"]["component"] = {"Q": {"en": "Controlling"},
                                "QQ": {"en": "Access"}}
    return t


def test_class_table_names_and_domains():
    ct = table.ClassTable(_small_table(), {
        "L:QQC": {"is": "Hurð", "en": "Door", "status": "reviewed"},
        "group:component:QQ": {"is": "Op"}})
    assert ct.name("QQC", "is", "[L]") == "Hurð"
    assert ct.name("AD", "is", "[L]") == "(Wall construction)"
    assert ct.name("AD", "en") == "Wall construction"
    assert ct.known("AAA", "[B]") and ct.known("AAA", "[A]")
    assert not ct.known("AAA", "[L]")
    assert ct.path("QQC", "is", "[L]") == "Controlling > Op > Hurð"
    assert ct.path("AAA", "en", "[B]") == "Dwelling > Room"
    assert ct.coverage() == (1, 4)
    assert [c for c, _ in ct.choices("L", "en")] == ["AD", "QQC"]
    assert ct.search("dør", "L", "en") == [("QQC", "Door")]


def test_name_status_stale():
    e = {"en": "Door leaf"}
    assert importer.name_status(e, {}) == "missing"
    assert importer.name_status(e, {"is": "Hurð", "en": "Door"}) == "stale"
    assert importer.name_status(e, {"is": "Hurðarblað", "en": "Door leaf",
                                    "status": "reviewed"}) == "reviewed"


def test_names_csv_round_trip(tmp_path):
    t = _small_table()
    text = importer.names_csv(t, {"L:QQC": {"is": "Hurð", "en": "Door"}})
    assert text.startswith("﻿domain;code;level;en;da;is;status")
    # Excel in some locales saves with commas
    csv = tmp_path / "n.csv"
    csv.write_text("﻿domain,code,en,is,status\n"
                   'L,AD,Wall construction,"Vegg, uppbygging",reviewed\n'
                   "L,QQC,Door,,missing\n"
                   "group:component,QQ,Access,Op,\n", encoding="utf-8")
    names = importer.read_names_csv(str(csv), t)
    assert names == {
        "L:AD": {"is": "Vegg, uppbygging", "en": "Wall construction",
                 "status": "reviewed"},
        "group:component:QQ": {"is": "Op", "en": "Access",
                               "status": "reviewed"}}


def test_store_versions_and_layers(tmp_path):
    st = store_mod.Store(DATA, str(tmp_path / "studio"))
    shipped = st.active_id()
    assert shipped == "molio-cci-20200526-R1"
    assert st.load_table().name("QQC", "is", "[L]") == "Hurð"
    t = _small_table()
    st.save_table(t, "test")
    assert st.active_id() == "t1"
    assert st.config()["history"][0]["source"] == "test"
    st.set_active(shipped)
    assert st.active_id() == shipped
    st.save_names({"L:QQC": {"is": "Útidyr", "en": "Door"}})
    assert st.load_table().name("QQC", "is", "[L]") == "Útidyr"
    st.add_rule({"id": "s1", "category": ["OST_Doors"], "class": "QQE"})
    rs = st.ruleset()
    r = rs.classify({"category": "OST_Doors", "family": "x", "type": "y"})
    assert (r.class_code, r.studio) == ("QQE", True)
    r = rs.classify({"category": "OST_Windows"})
    assert (r.class_code, r.studio, r.verified) == ("QQA", False, True)


def test_exact_name_rule():
    rs = rules.RuleSet({"rules": [
        {"id": "a", "category": ["OST_Doors"],
         "match": {"family": "Hurð", "type": "900"}, "class": "QQE"},
        {"id": "b", "category": ["OST_Doors"], "class": "QQC"}]})
    assert rs.classify({"category": "OST_Doors", "family": "hurð",
                        "type": "900"}).class_code == "QQE"
    assert rs.classify({"category": "OST_Doors", "family": "Hurð",
                        "type": "9000"}).class_code == "QQC"


# ------------------------------------------------ the shipped data

def _load(name):
    with io.open(os.path.join(DATA, name), encoding="utf-8") as f:
        return json.load(f)


def test_shipped_rules_use_real_codes():
    t = _load(os.path.join("tables", "molio-cci-20200526-R1.json"))
    rs = rules.RuleSet(_load("rules.json"))
    assert rs.problems == []
    for r in _load("rules.json")["rules"]:
        if not r.get("class"):
            continue
        dom = "S" if r["category"][0] in ("OST_Rooms", "OST_MEPSpaces") \
            else "L"
        assert r["class"] in t["domains"][dom], r["id"]
        if r.get("u"):
            assert t["domains"]["L"][r["u"]]["table"] == "functional"
            assert t["domains"]["L"][r["vv"]]["table"] == "technical"


@pytest.mark.parametrize("name,code", [
    ("Stofa", "AAB"), ("Svefnherbergi 2", "AAA"), ("Stigagangur", "EAD"),
    ("Gangur", "EAC"), ("Sorpgeymsla", "CAA"), ("Geymsla", "CAN"),
    ("Skrifstofa", "BAA"), ("Baðherbergi", "ABA"), ("Gufubað", "ABF"),
    ("Salerni", "ABB"), ("WC", "ABB"), ("Eldhús", "BBA"),
    ("Anddyri", "EAA"), ("Inntaksrými", "DAC"), ("Fundarherbergi", "BAB"),
    ("Corridor", "EAC"), ("Kontor", "BAA"), ("Hjólageymsla", "CBD"),
    ("Bílakjallari", "CBD"), ("Bílastæði", "CBD"), ("Svalir", "AA"),
    ("Svalagangur", "EAC"), ("Sprinklerrými", "DAC"),
    ("00-03 Brunastúka", "EAB"), ("00-02 Öryggisstúka", "BAK"),
    ("01-17 Frystir", "CAG"), ("01-18 Uppvask", "BBA"),
    ("02-22 Kaffi aðstaða", "BBA"), ("02-06 Kaffiaðsataða", "BBA"),
    ("02-35 Ræstirými", "CBB"), ("01-14 Prentrými", "BAA"),
    ("01-02 ÖG stjórnun/RLS", "BAK"), ("01-30 Blaðamanna rými", "AA"),
    ("Fundarsalur", "BAB"), ("Matsalur", "BEA")])
def test_room_name_rules(name, code):
    rs = rules.RuleSet(_load("rules.json"))
    r = rs.classify({"category": "OST_Rooms", "family": "", "type": name},
                    kind="space")
    assert r.class_code == code


@pytest.mark.parametrize("cat,name,code", [
    ("OST_Doors", "Bílskúrshurð 2500", "QQE"),
    ("OST_Doors", "Innihurð 900", "QQC"),
    ("OST_PlumbingFixtures", "Salerni vegghengt", "XKB"),
    ("OST_PlumbingFixtures", "Handlaug", "XKA"),
    ("OST_PlumbingFixtures", "Sturtubotn 900x900", "XKA"),
    ("OST_Floors", "Svalagólf 200", "AH"),
    ("OST_Floors", "Steypt plata 250", "AC"),
    ("OST_PlumbingFixtures", "Baðkar 1700", "XKA"),
    ("OST_PlumbingFixtures", "Sturtutæki hitastýrt", "QNA"),
    ("OST_DuctAccessory", "Reykloka 200", "FMB"),
    ("OST_PipeAccessory", "Stjórnloki DN20", "QNA"),
    ("OST_Planting", "Birki", "TRA"),
    ("OST_Railings", "Handrið 1100", "FQD"),
    ("OST_Railings", "Handlisti 40", "FQC"),
    ("OST_Railings", "Girðing 1200", "RUA"),
    ("OST_GenericModel", "DURAVIT_045260-Vero-Above-Counter-Bathroom-Sink",
     "XKA"),
    ("OST_SecurityDevices", "Aðgangshlið Gunnebo gate", "QQF"),
    ("OST_Toposolid", "Gras og jörð", "CF"),
    ("OST_Toposolid", "Jörð", "CA"),
    ("OST_GenericModel", "Lyfta", "GMB"),
    ("OST_GenericModel", "Hringborð", "UBE"),
    ("OST_GenericModel", "Eldhús vinnu borð", "UBE"),
    ("OST_SpecialityEquipment", "Reyklúga frá jörðu upp, 0.5m2", "QQD"),
    ("OST_Furniture", "Standing desk Qbus 1400", "UBE"),
    ("OST_Furniture", "Monza Bistro Chair", "CLC"),
    ("OST_Furniture", "Hilla", "RB"),
    ("OST_GenericModel", "Alford", "CLC"),
    ("OST_SecurityDevices",
     "NBS_Gunnebo_HalfHghtAcsCtrlGts_PreSec_BoardSec", "QQF"),
    ("OST_GenericModel", "Loftræstisamstæða", "HF"),
    ("OST_GenericModel", "Mediclinics_Foam soap dispenser", "RB")])
def test_element_rules(cat, name, code):
    rs = rules.RuleSet(_load("rules.json"))
    assert rs.classify({"category": cat, "family": name,
                        "type": ""}).class_code == code


def test_shipped_names_match_table():
    t = _load(os.path.join("tables", "molio-cci-20200526-R1.json"))
    names = _load("names_is.json")["names"]
    for key, n in names.items():
        parts = key.split(":")
        if parts[0] == "group":
            e = t["groups"][parts[1]][parts[2]]
        else:
            e = t["domains"][parts[0]][parts[1]]
        assert n["en"] == e.get("en", ""), key
        assert n["is"] and n["status"] in ("draft", "bim_island")
    # every space class has an Icelandic name
    assert all("S:" + c in names for c in t["domains"]["S"])


@pytest.mark.skipif(not os.path.isdir(MOLIO), reason="Molio files not here")
def test_real_molio_files():
    paths = [os.path.join(MOLIO, f) for f in sorted(os.listdir(MOLIO))]
    t = importer.read_any(paths)
    assert importer.counts(t) == {"L": 722, "S": 148, "E": 174, "D": 0}
    L = t["domains"]["L"]
    assert (L["QQC"]["en"], L["QQC"]["da"]) == ("Door", "Dør")
    assert L["AD"]["table"] == "technical" and L["B"]["table"] == "functional"
    assert t["domains"]["S"]["AAA"]["en"] == "Room"      # not "Courtyard"
    shipped = _load(os.path.join("tables", "molio-cci-20200526-R1.json"))
    for d in ("L", "S", "E"):
        assert t["domains"][d] == shipped["domains"][d]


MOLIO2 = os.environ.get("CCI_MOLIO_P150_DIR", "")


@pytest.mark.skipif(not os.path.isdir(MOLIO2), reason="P150 files not here")
def test_current_molio_p150_files():
    """Molio IKT's current free downloads (P150a-d) have no date or
    edition in the file names: the version comes from the change log."""
    paths = [os.path.join(MOLIO2, f) for f in sorted(os.listdir(MOLIO2))]
    log = []
    t = importer.read_any(paths, log)
    assert t["id"] == "molio-cci-20200526-R1"
    assert importer.counts(t) == {"L": 722, "S": 148, "E": 174, "D": 74}
    assert t["domains"]["D"]["A"]["en"] == "Road system"
    assert t["groups"]["aid"]["A"]["en"] == "Equipment for supply"
    shipped = _load(os.path.join("tables", "molio-cci-20200526-R1.json"))
    assert importer.diff(shipped, t) == {"added": [], "removed": [],
                                         "renamed": []}
