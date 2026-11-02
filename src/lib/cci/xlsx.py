# -*- coding: utf-8 -*-
"""Minimal .xlsx reader: sheet names and cell values as text.

Uses only zipfile and ElementTree so it runs in pyRevit's IronPython 2.7
as well as CPython 3 (no openpyxl in Revit). Reads shared strings, inline
strings and numbers; ignores styles, formulas (uses cached values) and
dates (returned as the raw number).
"""
from __future__ import unicode_literals

import re
import zipfile
import xml.etree.ElementTree as ET

from cci import compat

_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
_PKG = "{http://schemas.openxmlformats.org/package/2006/relationships}"
_COL = re.compile(r"^([A-Z]+)(\d+)$")


def _col_index(letters):
    n = 0
    for ch in letters:
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def _text(el):
    """All text inside an <si> or <is> element (rich text runs joined)."""
    parts = []
    for t in el.iter(_NS + "t"):
        parts.append(t.text or "")
    return "".join(parts)


class Workbook(object):

    def __init__(self, path):
        self._zip = zipfile.ZipFile(path)
        names = set(self._zip.namelist())
        self._strings = []
        if "xl/sharedStrings.xml" in names:
            root = ET.fromstring(self._zip.read("xl/sharedStrings.xml"))
            self._strings = [_text(si) for si in root.findall(_NS + "si")]
        rels = {}
        rel_root = ET.fromstring(self._zip.read("xl/_rels/workbook.xml.rels"))
        for rel in rel_root.findall(_PKG + "Relationship"):
            target = rel.get("Target")
            if target.startswith("/"):
                target = target[1:]
            elif not target.startswith("xl/"):
                target = "xl/" + target
            rels[rel.get("Id")] = target
        wb_root = ET.fromstring(self._zip.read("xl/workbook.xml"))
        self.sheets = []
        for s in wb_root.iter(_NS + "sheet"):
            self.sheets.append((compat.to_text(s.get("name")),
                                rels.get(s.get(_REL + "id"))))

    @property
    def sheet_names(self):
        return [n for n, _ in self.sheets]

    def rows(self, sheet_name):
        """List of rows; each row is a list of text ('' for empty)."""
        target = dict(self.sheets)[sheet_name]
        root = ET.fromstring(self._zip.read(target))
        out = []
        for row in root.iter(_NS + "row"):
            r = int(row.get("r") or (len(out) + 1)) - 1
            while len(out) < r:
                out.append([])
            cells = []
            for c in row.findall(_NS + "c"):
                ref = c.get("r")
                if ref:
                    m = _COL.match(ref)
                    i = _col_index(m.group(1))
                else:
                    i = len(cells)
                while len(cells) < i:
                    cells.append("")
                cells.append(self._value(c))
            out.append(cells)
        return out

    def _value(self, c):
        t = c.get("t")
        if t == "inlineStr":
            el = c.find(_NS + "is")
            return _text(el) if el is not None else ""
        v = c.find(_NS + "v")
        if v is None or v.text is None:
            return ""
        if t == "s":
            try:
                return self._strings[int(v.text)]
            except (IndexError, ValueError):
                return ""
        text = compat.to_text(v.text)
        if t is None and re.match(r"^-?\d+\.0$", text):
            text = text[:-2]
        return text

    def close(self):
        self._zip.close()
