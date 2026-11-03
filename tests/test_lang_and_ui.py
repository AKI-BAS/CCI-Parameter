# -*- coding: utf-8 -*-
"""Both languages complete and consistent; scripts only use names that
exist in their XAML."""
import io
import json
import os
import re
import string
import sys
import xml.etree.ElementTree as ET

import pytest

ROOT = os.path.join(os.path.dirname(__file__), "..")
SRC = os.path.join(ROOT, "src")
sys.path.insert(0, os.path.join(SRC, "lib"))

from cci import formats, groups  # noqa: E402

LANGS = {}
for lang in ("is", "en"):
    with io.open(os.path.join(SRC, "lang", lang + ".json"),
                 encoding="utf-8") as f:
        LANGS[lang] = json.load(f)


def _sources():
    for base, _, files in os.walk(SRC):
        for name in files:
            if name.endswith(".py"):
                path = os.path.join(base, name)
                with io.open(path, encoding="utf-8") as f:
                    yield path, f.read()


def _placeholders(text):
    return sorted(set(f[1] for f in string.Formatter().parse(text)
                      if f[1]))


def test_same_keys():
    assert set(LANGS["is"]) == set(LANGS["en"])


@pytest.mark.parametrize("key", sorted(LANGS["en"]))
def test_same_placeholders(key):
    assert _placeholders(LANGS["is"][key]) == _placeholders(LANGS["en"][key])


def _expected_keys():
    keys = set()
    call = re.compile(r"""\b(?:t|alert|confirm|Tx)\((?:doc,\s*|d,\s*)?"""
                      r"""["']([a-z_]+\.[a-z_.]+)["']""")
    literal = re.compile(r"""["']((?:fmt|chk|loc|set|rules|setup|params|imp|table"""
                         r"""|classify|number|check|ifc|msg|tx)\.[a-z_.]+)"""
                         r"""["']""")
    for _, text in _sources():
        keys.update(k for k in call.findall(text) if not k.endswith("_"))
        keys.update(k for k in literal.findall(text)
                    if not k.endswith((".", "_", ".json")))
    for sc in groups.SCOPES:
        keys.update(["scope." + sc, "scope." + sc + ".d"])
    keys.update("group." + g for g in groups.GROUP_IDS)
    keys.update("topnode." + tn for tn in formats.TOPNODES)
    keys.update("sev." + s for s in ("error", "warning", "info"))
    for b in ("setup", "params", "table", "classify", "number",
              "locations", "check", "ifc", "guide"):
        keys.update(["btn.%s.title" % b, "btn.%s.tip" % b])
    keys.update("panel." + p for p in ("setup", "classify", "deliver", "help"))
    keys.update("params." + g for g in ("added", "updated", "unchanged",
                                        "missing", "wrong_type", "conflict",
                                        "other_file"))
    keys.update("setup.roomnum." + m for m in ("as_is", "last_segment",
                                               "auto"))
    keys.update("setup.doorroom." + m for m in ("to", "from"))
    keys.update("setup.mlnum." + m for m in ("type", "instance"))
    chk = [k for k in keys if k.startswith("chk.") and not
           k.endswith(".h")]
    keys.update(k + ".h" for k in chk)
    return keys


def test_all_used_keys_exist():
    missing = sorted(k for k in _expected_keys() if k not in LANGS["en"])
    assert missing == []


def test_validator_keys_exist():
    for check in set(formats.VALIDATORS.values()):
        for value in ("", "x", "+x", "[X]", "§", "#", "=", "%"):
            key = check(value)
            if key:
                assert key in LANGS["en"], key


@pytest.mark.parametrize("button", ["setup", "classify"])
def test_xaml_names(button):
    folder = os.path.join(SRC, "buttons", button)
    tree = ET.parse(os.path.join(folder, "ui.xaml"))
    xns = "{http://schemas.microsoft.com/winfx/2006/xaml}Name"
    names = set(el.get(xns) for el in tree.iter() if el.get(xns))
    handlers = set()
    for el in tree.iter():
        for attr in ("Click", "TextChanged"):
            if el.get(attr):
                handlers.add(el.get(attr))
    with io.open(os.path.join(folder, "script.py"), encoding="utf-8") as f:
        script = f.read()
    used = set(re.findall(r"self\.([a-z_]+(?:_b|_cb|_tb|_l|_dg|_d|_h))\b",
                          script))
    used |= set(re.findall(r"self\.(tab_[a-z]+|grid|intro|status|"
                           r"scope_[a-z]+)\b", script))
    # names built in a loop: sc_<scope> and sc_<scope>_d
    if button == "setup":
        for sc in groups.SCOPES:
            assert "sc_" + sc in names and "sc_" + sc + "_d" in names
    assert sorted(used - names) == []
    for h in handlers:
        assert "def %s(self" % h in script, h


def test_no_mojibake_and_icelandic_used():
    for key, text in LANGS["is"].items():
        assert "Ã" not in text, key
    joined = " ".join(LANGS["is"].values())
    for ch in u"áðéíóúýþæö":
        assert ch in joined
