# -*- coding: utf-8 -*-
"""Read CCI classification tables into the tool's table format.

Accepts:
  - Molio's spreadsheets (.xlsx), Danish and/or English editions, for
    construction elements (functional systems, technical systems,
    components), use of spaces and use of construction entities;
  - a table already in the tool's own format (.json), e.g. one the studio
    publishes on a shared drive or a web address.

Several files are merged: Danish terms are taken from the Danish edition,
English terms from the English one, and any disagreement is reported.

Table format (version 1):

    {"format": 1, "id": "molio-cci-20200526-R1", "name": "...",
     "publisher": "Molio", "date": "2020-05-26", "edition": "R1",
     "files": [...], "complete": true,
     "domains": {"L": {code: entry}, "S": {...}, "E": {...}},
     "groups":  {"component": {"Q": entry, "QQ": entry},
                 "technical": {"A": entry}}}

    entry = {"en", "da", "def_en", "def_da", "level", "table"}

Domain L holds construction elements ([L]): functional systems (1
letter), technical systems (2) and components (3). S holds use of spaces
(for [A]/[B]), E use of construction entities ([E]).
"""
from __future__ import unicode_literals

import io
import os
import re

from cci import compat

FORMAT = 1
DOMAINS = ("L", "S", "E", "D")
FIELDS = ("en", "da", "def_en", "def_da")

_KINDS = [
    ("functional", ("functional", "funktionel")),
    ("technical", ("technical", "teknisk")),
    ("component", ("component", "komponent")),
    ("space", ("spaces", "rumanvendelse")),
    ("entity", ("entities", "bygværksanvendelse", "bygvaerksanvendelse",
                "klasser af bygværk")),
]
_CODE = re.compile(r"^([A-Z]{1,3})_*$")
_LEVEL_HEAD = re.compile(r"^(level|niv)\.?\s*\d", re.I)


class ImportError_(Exception):
    """Raised with an i18n key and params."""

    def __init__(self, key, **params):
        Exception.__init__(self, key)
        self.key = key
        self.params = params


def sheet_kind(name):
    low = name.lower()
    if "change" in low or "lookup" in low or "log" in low:
        return None
    for kind, words in _KINDS:
        for w in words:
            if w in low:
                return kind
    return None


def _clean(value):
    if value is None:
        return ""
    value = compat.to_text(value).replace("﻿", "")
    value = value.replace("*", "")
    value = re.sub(r"\s+", " ", value).strip()
    return "" if value in ("0", "-") else value


def _field_of(header):
    h = header.strip().lower()
    if h in ("term (en)", "term (uk)", "engelsk hovedbegreb"):
        return "en"
    if h in ("term (dk)", "term (da)", "hovedbegreb"):
        return "da"
    if h in ("definition (en)", "definition (uk)", "engelsk definition"):
        return "def_en"
    if h in ("definition (dk)", "definition (da)", "bygningsdel definition"):
        return "def_da"
    return None


def parse_sheet(rows, kind):
    """[(code, level, {field: text})], primary language ('en'/'da')."""
    head = None
    for i, row in enumerate(rows):
        if any(_LEVEL_HEAD.match(c or "") for c in row):
            head = i
            break
    if head is None:
        return [], None
    header = rows[head]
    code_cols = [j for j, c in enumerate(header)
                 if _LEVEL_HEAD.match(c or "")]
    fields = {}
    primary = None
    # Term headers are normally on the "Level 1" row; some sheets (e.g.
    # construction aids) put them on a row above it.
    candidates = [header] + [rows[i] for i in range(head - 1, -1, -1)]
    for row in candidates:
        found = {}
        for j, c in enumerate(row):
            f = _field_of(c or "")
            if f and f not in found:
                found[f] = j
        if found:
            fields = found
            for j in sorted(found.values()):
                f = [k for k, v in found.items() if v == j][0]
                if f in ("en", "da"):
                    primary = f
                    break
            break
    out = []
    for row in rows[head + 1:]:
        code = ""
        for j in code_cols:
            if j < len(row) and _clean(row[j]):
                code = _clean(row[j])
                break
        m = _CODE.match(code)
        if not m:
            continue
        values = {}
        for f, j in fields.items():
            values[f] = _clean(row[j]) if j < len(row) else ""
        if not values.get("en") and not values.get("da"):
            continue
        out.append((m.group(1), len(m.group(1)), values))
    return out, primary


def _place(kind, code, level):
    """(bucket, key) where a parsed row belongs."""
    if kind == "functional":
        return ("L", code) if level == 1 else (None, None)
    if kind == "technical":
        if level == 1:
            return ("group:technical", code)
        return ("L", code)
    if kind == "component":
        if level < 3:
            return ("group:component", code)
        return ("L", code)
    if kind == "space":
        return ("S", code)
    if kind == "entity":
        return ("E", code)
    if kind == "aid_functional":
        return ("D", code) if level == 1 else (None, None)
    if kind == "aid_component":
        if level == 1:
            return ("group:aid", code)
        return ("D", code)
    return (None, None)


def _is_aids(wb, path):
    """Molio's table of construction aids (materiel, [D]) reuses the sheet
    names 'Functional systems' and 'Components'."""
    if re.search(r"aid|materiel", os.path.basename(path), re.I):
        return True
    for name in wb.sheet_names[:1]:
        for row in wb.rows(name)[:8]:
            for c in row:
                low = (c or "").lower()
                if low in ("construction aid", "materiel"):
                    return True
    return False


def _excel_date(serial):
    import datetime
    try:
        d = datetime.date(1899, 12, 30) + \
            datetime.timedelta(days=int(float(serial)))
        return d.isoformat()
    except (ValueError, TypeError, OverflowError):
        return ""


def _change_log_version(rows):
    """(date, edition) of the last 'R<n>' release in a change log."""
    best = ("", "")
    for row in rows:
        if len(row) < 2:
            continue
        m = re.match(r"^(R\d+)$", (row[1] or "").strip())
        if m:
            date = _excel_date(row[0]) or ""
            if (date, m.group(1)) > best:
                best = (date, m.group(1))
    return best


def _version_of(paths, dates=None, eds=None):
    dates, eds = list(dates or []), list(eds or [])
    for p in paths:
        name = os.path.basename(p)
        m = re.search(r"(20\d{2})[-_]?(\d{2})[-_]?(\d{2})", name)
        if m:
            dates.append("%s-%s-%s" % m.groups())
        m = re.search(r"[_\- ](R\d+)(?=[_\-. ])", name + ".")
        if m:
            eds.append(m.group(1))

    def most(values):
        return max(set(values), key=values.count) if values else ""
    return most(dates), most(eds)


def empty_table():
    return {"format": FORMAT, "id": "", "name": "", "publisher": "",
            "date": "", "edition": "", "files": [], "complete": True,
            "domains": dict((d, {}) for d in DOMAINS),
            "groups": {"component": {}, "technical": {}, "aid": {}}}


def _bucket(table, name):
    if name.startswith("group:"):
        return table["groups"].setdefault(name[6:], {})
    return table["domains"].setdefault(name, {})


def read_xlsx(paths, log=None):
    """Merge Molio spreadsheets into one table. log: list for messages
    (tuples of i18n key and params)."""
    from cci import xlsx
    log = log if log is not None else []
    table = empty_table()
    # value -> which language the file it came from is in
    origin = {}
    found_any = False
    log_dates, log_eds = [], []
    for path in paths:
        wb = xlsx.Workbook(path)
        try:
            aids = _is_aids(wb, path)
            for name in wb.sheet_names:
                if "change" in name.lower():
                    date, ed = _change_log_version(wb.rows(name))
                    if ed:
                        log_dates.append(date)
                        log_eds.append(ed)
                    continue
                kind = sheet_kind(name)
                if not kind:
                    continue
                if aids:
                    if kind not in ("functional", "component"):
                        continue
                    kind = "aid_" + kind
                parsed, primary = parse_sheet(wb.rows(name), kind)
                if not parsed:
                    continue
                found_any = True
                log.append(("imp.sheet", {"file": os.path.basename(path),
                                          "sheet": name, "n": len(parsed)}))
                for code, level, values in parsed:
                    bucket, key = _place(kind, code, level)
                    if bucket is None:
                        continue
                    entries = _bucket(table, bucket)
                    entry = entries.setdefault(key, {"level": level,
                                                     "table": kind})
                    for f in FIELDS:
                        new = values.get(f, "")
                        if not new:
                            continue
                        old = entry.get(f, "")
                        lang = f[-2:]
                        mine = (primary == lang)
                        okey = (bucket, key, f)
                        if not old:
                            entry[f] = new
                            origin[okey] = mine
                        elif old != new:
                            if mine and not origin.get(okey):
                                entry[f] = new
                                origin[okey] = True
                            elif f in ("en", "da") and \
                                    old.lower() != new.lower():
                                item = ("imp.conflict", {
                                    "code": key, "field": f, "kept": old,
                                    "other": new})
                                if item not in log:
                                    log.append(item)
        finally:
            wb.close()
    if not found_any:
        raise ImportError_("imp.no_sheets")
    date, edition = _version_of(paths, [d for d in log_dates if d],
                                log_eds)
    table["date"] = date
    table["edition"] = edition
    table["publisher"] = "Molio"
    table["id"] = "molio-cci-%s-%s" % (date.replace("-", "") or "x",
                                       edition or "x")
    table["name"] = "Molio CCI %s %s" % (date, edition)
    table["files"] = [os.path.basename(p) for p in paths]
    return table


def read_json(path):
    data = compat.load_json(path)
    return check_table(data)


def check_table(data):
    if not isinstance(data, dict) or data.get("format") != FORMAT:
        raise ImportError_("imp.bad_json")
    for d in DOMAINS:
        data.setdefault("domains", {}).setdefault(d, {})
    data.setdefault("groups", {}).setdefault("component", {})
    data["groups"].setdefault("technical", {})
    data["groups"].setdefault("aid", {})
    if not data.get("id"):
        raise ImportError_("imp.no_id")
    if not any(data["domains"].values()):
        raise ImportError_("imp.empty")
    return data


def read_any(paths, log=None):
    paths = list(paths)
    jsons = [p for p in paths if p.lower().endswith(".json")]
    sheets = [p for p in paths if p.lower().endswith(".xlsx")]
    other = [p for p in paths if p not in jsons and p not in sheets]
    if other:
        raise ImportError_("imp.bad_type", file=os.path.basename(other[0]))
    if jsons and sheets:
        raise ImportError_("imp.mixed")
    if len(jsons) > 1:
        raise ImportError_("imp.one_json")
    if jsons:
        return read_json(jsons[0])
    return read_xlsx(sheets, log)


def counts(table):
    return dict((d, len(table["domains"].get(d, {}))) for d in DOMAINS)


def diff(old, new):
    """{"added": [(domain, code)], "removed": [...], "renamed":
    [(domain, code, old_en, new_en)]}"""
    out = {"added": [], "removed": [], "renamed": []}
    for d in DOMAINS:
        a = (old or {}).get("domains", {}).get(d, {})
        b = new.get("domains", {}).get(d, {})
        for code in sorted(set(b) - set(a)):
            out["added"].append((d, code))
        for code in sorted(set(a) - set(b)):
            out["removed"].append((d, code))
        for code in sorted(set(a) & set(b)):
            ea, eb = a[code].get("en", ""), b[code].get("en", "")
            if ea and eb and ea != eb:
                out["renamed"].append((d, code, ea, eb))
    return out


# ------------------------------------------------- Icelandic names (CSV)

CSV_COLUMNS = ("domain", "code", "level", "en", "da", "is", "status")


def names_csv(table, names, lang_names=None):
    """Text of a CSV (semicolon, UTF-8 with BOM for Excel) with every class
    and its Icelandic name, for translating or reviewing in Excel."""
    lines = [";".join(CSV_COLUMNS)]

    def cell(v):
        v = compat.to_text(v if v is not None else "")
        if ";" in v or '"' in v or "\n" in v:
            v = '"' + v.replace('"', '""') + '"'
        return v
    for d in DOMAINS:
        for code in sorted(table["domains"].get(d, {})):
            e = table["domains"][d][code]
            n = names.get(d + ":" + code, {})
            lines.append(";".join(cell(x) for x in (
                d, code, e.get("level", ""), e.get("en", ""),
                e.get("da", ""), n.get("is", ""), name_status(e, n))))
    for g in ("component", "technical", "aid"):
        for code in sorted(table["groups"].get(g, {})):
            e = table["groups"][g][code]
            key = "group:%s:%s" % (g, code)
            n = names.get(key, {})
            lines.append(";".join(cell(x) for x in (
                "group:" + g, code, e.get("level", ""), e.get("en", ""),
                e.get("da", ""), n.get("is", ""), name_status(e, n))))
    return "﻿" + "\r\n".join(lines) + "\r\n"


def name_status(entry, name):
    if not name.get("is"):
        return "missing"
    if name.get("en") and entry.get("en") and name["en"] != entry["en"]:
        return "stale"
    return name.get("status") or "draft"


def _split_csv_line(line, sep):
    out, cur, quoted, i = [], [], False, 0
    while i < len(line):
        ch = line[i]
        if quoted:
            if ch == '"':
                if i + 1 < len(line) and line[i + 1] == '"':
                    cur.append('"')
                    i += 1
                else:
                    quoted = False
            else:
                cur.append(ch)
        elif ch == '"':
            quoted = True
        elif ch == sep:
            out.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
        i += 1
    out.append("".join(cur))
    return out


def read_names_csv(path, table):
    """{key: {"is", "en", "status"}} from an edited CSV. Rows with an
    empty Icelandic name are skipped. Excel may save with ',' or ';'."""
    with io.open(path, "r", encoding="utf-8-sig") as f:
        text = f.read()
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        raise ImportError_("imp.csv_empty")
    sep = ";" if lines[0].count(";") >= lines[0].count(",") else ","
    head = [h.strip().lower() for h in _split_csv_line(lines[0], sep)]
    for col in ("domain", "code", "is"):
        if col not in head:
            raise ImportError_("imp.csv_columns")
    idx = dict((h, i) for i, h in enumerate(head))
    out = {}
    for ln in lines[1:]:
        cells = _split_csv_line(ln, sep)

        def get(col):
            i = idx.get(col)
            return cells[i].strip() if i is not None and i < len(cells) \
                else ""
        name = get("is")
        dom, code = get("domain"), get("code").upper()
        if not name or not code:
            continue
        if dom.startswith("group:"):
            key = "group:%s:%s" % (dom[6:], code)
            entry = table["groups"].get(dom[6:], {}).get(code, {})
        else:
            key = dom + ":" + code
            entry = table["domains"].get(dom, {}).get(code, {})
        status = get("status") or "reviewed"
        if status in ("missing", "stale"):
            status = "reviewed"
        out[key] = {"is": name, "en": entry.get("en", ""),
                    "status": status}
    return out


# ----------------------------------------------------------------- links

def split_links(text):
    """One or more links/paths, separated by new lines, ';' or spaces."""
    parts = re.split(r"[\s;]+", (text or "").strip())
    return [p.strip().strip('"') for p in parts if p.strip().strip('"')]


def guess_ext(url, head):
    """'.xlsx' / '.json' from the address, else from the first bytes."""
    low = url.lower().split("?")[0]
    for ext in (".xlsx", ".json"):
        if low.endswith(ext):
            return ext
    if head[:2] == b"PK":
        return ".xlsx"
    if head.lstrip(b"\xef\xbb\xbf \r\n\t")[:1] in (b"{", b"["):
        return ".json"
    return None
