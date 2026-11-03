# -*- coding: utf-8 -*-
"""The Guide window's content: both languages, generated tables, the
inline markup, the CCI browser and the model status rows."""
import io
import json
import os
import re
import sys
import types

import pytest

HERE = os.path.dirname(__file__)
SRC = os.path.join(HERE, "..", "src")
sys.path.insert(0, os.path.join(SRC, "lib"))
sys.path.insert(0, HERE)

from cci import formats, groups, guide, i18n  # noqa: E402
from cci.table import ClassTable  # noqa: E402


def _table():
    with io.open(os.path.join(SRC, "data", "tables",
                              "molio-cci-20200526-R1.json"),
                 encoding="utf-8") as f:
        data = json.load(f)
    with io.open(os.path.join(SRC, "data", "names_is.json"),
                 encoding="utf-8") as f:
        names = json.load(f)["names"]
    return ClassTable(data, names)


def _pages(lang):
    i18n.load(os.path.join(SRC, "lang", lang + ".json"))
    return guide.pages(lang, _table())


def _texts(blocks):
    for b in blocks:
        if "text" in b:
            yield b["text"]
        for item in b.get("items", []):
            yield item
        for cell in b.get("head", []):
            yield cell
        for row in b.get("rows", []):
            for cell in row:
                yield cell


@pytest.fixture(autouse=True)
def _reset():
    yield
    i18n.load(os.path.join(SRC, "lang", "en.json"))


def test_same_pages_and_shape_in_both_languages():
    a, b = _pages("is"), _pages("en")
    assert [p["id"] for p in a] == [p["id"] for p in b]
    assert [p["id"] for p in a] == ["steps", "cci", "params", "lod",
                                    "scope", "faq", "browser", "glossary"]
    for pa, pb in zip(a, b):
        assert [x["t"] for x in pa["blocks"]] == \
            [x["t"] for x in pb["blocks"]], pa["id"]
        assert pa["title"] != pb["title"]


@pytest.mark.parametrize("lang", ["is", "en"])
def test_no_missing_text_keys_and_markup_closed(lang):
    for page in _pages(lang):
        for text in _texts(page["blocks"]):
            assert not re.search(r"\[[a-z]+\.[a-z_.]+\]", text), text
            assert text.count("**") % 2 == 0, text
            assert text.count("`") % 2 == 0, text


def test_language_really_switches():
    is_text = " ".join(t for p in _pages("is") for t in _texts(p["blocks"]))
    en_text = " ".join(t for p in _pages("en") for t in _texts(p["blocks"]))
    assert "Þróunarstig" in is_text and "þarf" in is_text
    assert "Level of development" in en_text
    assert " the " not in is_text.replace("the tool", "")[:2000]


def test_generated_tables_follow_the_data():
    pages = dict((p["id"], p) for p in _pages("en"))
    tables = [b for b in pages["params"]["blocks"] if b["t"] == "table"]
    names = " ".join(r[0] for r in tables[0]["rows"])
    for key in ("class", "type_id", "single_id", "location_at_id",
                "classification"):
        assert formats.PARAM[key] in names
    lod = [b for b in pages["lod"]["blocks"] if b["t"] == "table"]
    assert len(lod[-1]["rows"]) == len(groups.GROUP_IDS)
    openings = [r for r in lod[-1]["rows"]
                if r[0] == i18n.t("group.openings")][0]
    assert openings[1] == "LOD 325"
    scope = [b for b in pages["scope"]["blocks"] if b["t"] == "table"][0]
    assert len(scope["rows"]) == len(groups.SCOPES)
    topnodes = [b for b in pages["cci"]["blocks"] if b["t"] == "table"][-1]
    assert len(topnodes["rows"]) == len(formats.TOPNODES)
    # every Check message is explained
    faq = " ".join(_texts(pages["faq"]["blocks"]))
    for key in guide.faq_explain():
        assert i18n.t(key + ".h") in faq


def test_examples_in_the_guide_are_valid():
    for value, check in (("%QQC001", formats.check_type_id),
                         ("§B.AD.QQC001", formats.check_ml_type_id),
                         ("#QQC014", formats.check_single_id),
                         ("=H01.HD02.EGC001", formats.check_functional_id),
                         ("B01.01.001", formats.check_location_id),
                         ("+B01.01.101", formats.check_location_at_id),
                         ("QQC:Door", formats.check_classification)):
        assert check(value) is None, value
    t = _table()
    for code in ("B", "AD", "AC", "AE", "BD", "QQA", "QQC", "H", "HD",
                 "EGC"):
        assert t.known(code, "[L]"), code


def test_inline():
    assert guide.inline("a **b** `c` *d*") == [
        ("", "a "), ("b", "b"), ("", " "), ("c", "c"), ("", " "),
        ("i", "d")]
    assert guide.inline("100% * 2") == [("", "100% * 2")]
    assert guide.inline("") == []


def test_browser_detail():
    i18n.load(os.path.join(SRC, "lang", "is.json"))
    rows = dict(guide.browser_detail(_table(), "L", "QQC", "is"))
    assert rows["Kóði"] == "QQC"
    assert rows["Enska"] == "Door"
    assert "QQC:Door" in rows["Í Revit"]
    assert rows["Tegundarauðkenni"] == "%QQC001"
    assert "Space access object" in rows["Leið"] or "Hurð" in rows["Leið"]
    rows = dict(guide.browser_detail(_table(), "S", "AAB", "en"))
    assert rows["English"] == "Living space"
    assert guide.browser_detail(_table(), "L", "ZZZ", "en") == []


def test_model_status():
    i18n.load(os.path.join(SRC, "lang", "en.json"))
    guide.LANG[0] = "en"
    rows = guide.model_status({"setup": True, "params": (13, 13),
                               "types": (3, 5), "type_ids": (0, 0),
                               "rooms": (2, 2)})
    assert [r[1] for r in rows] == [True, True, False, None, True]
    assert rows[2][2] == "3 of 5"


# ------------------------------------------------- the button, faked WPF

class _Any(object):
    """Stands in for any WPF class: callable, any attribute, += works."""

    def __init__(self, *a, **k):
        self.__dict__["_items"] = []
        self.__dict__["Text"] = ""
        self.__dict__["SelectedIndex"] = 0

    def __getattr__(self, name):
        v = _Any()
        self.__dict__[name] = v
        return v

    def __call__(self, *a, **k):
        return _Any()

    def __iadd__(self, other):
        return self

    def Add(self, item):
        self._items.append(item)

    def Clear(self):
        del self._items[:]

    @property
    def Count(self):
        return len(self._items)


class _Mod(types.ModuleType):
    def __getattr__(self, name):
        return _Any()


def test_guide_button_runs(monkeypatch, tmp_path):
    import fake_revit as fr  # noqa: F401
    import runpy
    monkeypatch.setenv("APPDATA", str(tmp_path))
    for name in ("System.Windows", "System.Windows.Controls",
                 "System.Windows.Documents", "System.Windows.Media"):
        monkeypatch.setitem(sys.modules, name, _Mod(name))
    i18n.load(os.path.join(SRC, "lang", "is.json"))
    fr.STATE["doc"] = fr.Doc([])
    shown = {}

    def show(self):
        shown["tabs"] = self.tabs.Items._items
        self.status_click(None, None)
        self.find_tb.Text = "hurð"
        self.fill_list()
        shown["codes"] = list(self._codes)

    def init(self, xaml):
        self.tabs = _Any()

    monkeypatch.setattr(fr.WPFWindow, "__init__", init)
    monkeypatch.setattr(fr.WPFWindow, "ShowDialog", show)
    runpy.run_path(os.path.join(SRC, "buttons", "guide", "script.py"),
                   run_name="__main__")
    assert len(shown["tabs"]) == 8
    assert "QQC" in shown["codes"]
