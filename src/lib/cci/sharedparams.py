# -*- coding: utf-8 -*-
"""Revit shared parameter files for the CCI parameters.

Molio publishes the official CCI shared parameter file as tool C420 in
its paid "CAD og bygningsmodel" subscription. Until a studio has it, the
tool writes its own file with the same parameter names. Its GUIDs are
derived from the names (uuid5), so every copy of the tool, on every
machine and in every office, produces the same GUIDs.

What GUIDs matter for: Revit identifies a shared parameter by GUID, so
schedules, tags and copy/paste between models only line up when both
models use the same file. IFC export (CCI_in_Revit_to_IFC.txt) and
BIM Ísland's IDS checks go by parameter *name*, so they work with either
file. The Parameters button can later move a project from this file to
Molio's, keeping the values.
"""
from __future__ import unicode_literals

import io
import uuid

from cci import formats

NAMESPACE = uuid.UUID("5d1b7f0e-3c39-4d55-9a4e-3a7c2c1e0c11")
GROUP = "CCI"
FILE_NAME = "CCI_SharedParameters_CCI-tools.txt"

DESCRIPTIONS = {
    "class": "CCI classification code (X, XX or XXX), e.g. QQC",
    "class_t": "CCI classification code on the type, e.g. QQC",
    "topnode": "CCI domain (topnode), e.g. [L]",
    "topnode_t": "CCI domain (topnode) on the type, e.g. [L]",
    "type_id": "CCI type ID, e.g. %QQC001",
    "type_id_t": "CCI type ID on the type, e.g. %QQC001",
    "ml_type_id": "CCI multi-level type ID, e.g. §B.AD.QQC001",
    "functional_id": "CCI function ID, e.g. =H01.HD02.EGC001",
    "ml_location_id": "CCI room number, e.g. B01.01.001",
    "single_id": "CCI product ID, e.g. #QQC001",
    "location_at_id": "CCI location ID, e.g. +B01.01.001",
    "classification": "CCI classification for IFC export, e.g. AD",
    "classification_t": "CCI classification for IFC export on the type",
}

KEYS = list(formats.REQUIRED_PARAMS) + list(formats.OPTIONAL_PARAMS)
OWN_HEADER = ["# CCI parameters written by CCI-tools (BIM Ísland names). Same",
              "# GUIDs in every copy of the tool. Not Molio's C420 file."]


def guid_for(name):
    return uuid.uuid5(NAMESPACE, "cci-tools:" + name)


def own_entries():
    return [(formats.PARAM[k], guid_for(formats.PARAM[k]), "TEXT",
             DESCRIPTIONS[k]) for k in KEYS]


def file_text(entries=None, header=None):
    """Shared parameter file text. entries: [(name, guid, datatype,
    description)]; default: the tool's own CCI parameters."""
    if entries is None:
        entries = own_entries()
        header = OWN_HEADER if header is None else header
    lines = [
        "# This is a Revit shared parameter file.",
        "# Do not edit manually.",
    ] + list(header or []) + [
        "*META\tVERSION\tMINVERSION",
        "META\t2\t1",
        "*GROUP\tID\tNAME",
        "GROUP\t1\t%s" % GROUP,
        "*PARAM\tGUID\tNAME\tDATATYPE\tDATACATEGORY\tGROUP\tVISIBLE\t"
        "DESCRIPTION\tUSERMODIFIABLE\tHIDEWHENNOEXPRESSION",
    ]
    for name, guid, datatype, desc in entries:
        lines.append("PARAM\t%s\t%s\t%s\t\t1\t1\t%s\t1\t0" % (
            guid, name, datatype, (desc or "").replace("\t", " ")))
    return "\r\n".join(lines) + "\r\n"


def write_file(path, entries=None, header=None):
    """Revit reads and writes these files as UTF-16 LE with a BOM."""
    with io.open(path, "w", encoding="utf-16", newline="") as f:
        f.write(file_text(entries, header))
    return path


def read_text(path):
    raw = io.open(path, "rb").read()
    for enc in ("utf-16", "utf-8-sig", "cp1252"):
        try:
            text = raw.decode(enc)
            if "*PARAM" in text or "PARAM\t" in text:
                return text
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace")


def parse(text):
    """{name: {"guid", "datatype", "group"}} of the PARAM lines."""
    out = {}
    for line in text.splitlines():
        if not line.startswith("PARAM\t"):
            continue
        cells = line.split("\t")
        if len(cells) < 6:
            continue
        out[cells[2]] = {"guid": cells[1].lower(), "datatype": cells[3],
                         "group": cells[5]}
    return out


def is_tool_guid(name, guid):
    return str(guid).lower() == str(guid_for(name)).lower()


def check_file(text):
    """What a shared parameter file offers for CCI.

    Returns {"found": [...], "missing": [...], "not_text": [...],
             "case": {wanted: found_name}, "tool_file": bool}.
    'case' lists names that only differ in upper/lower case (e.g.
    CCITopNode vs CCITopnode): Revit treats those as different names.
    """
    params = parse(text)
    lower = dict((n.lower(), n) for n in params)
    out = {"found": [], "missing": [], "not_text": [], "case": {},
           "tool_file": False}
    tool = 0
    for key in KEYS:
        want = formats.PARAM[key]
        name = want if want in params else lower.get(want.lower())
        if name is None:
            if key in formats.REQUIRED_PARAMS:
                out["missing"].append(want)
            continue
        if name != want:
            out["case"][want] = name
        if params[name]["datatype"].upper() != "TEXT":
            out["not_text"].append(name)
        else:
            out["found"].append(name)
        if is_tool_guid(want, params[name]["guid"]):
            tool += 1
    out["tool_file"] = tool > 0 and tool == len(out["found"])
    return out
