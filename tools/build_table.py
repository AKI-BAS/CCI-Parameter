# -*- coding: utf-8 -*-
"""Build a table JSON from Molio's CCI spreadsheets (same importer the
Revit button uses).

    python tools/build_table.py <xlsx files...> [--out folder] [--ship]

--ship writes it into src/data/tables/ and makes it the shipped default.
The JSON can also be put on a shared drive or web address and loaded with
the "CCI table" button (Update from link).
"""
from __future__ import print_function, unicode_literals

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src", "lib"))

from cci import compat, importer  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--out", default=".")
    ap.add_argument("--ship", action="store_true")
    a = ap.parse_args()
    log = []
    table = importer.read_any(a.files, log)
    for key, p in log:
        print(key, p)
    data = os.path.join(HERE, "..", "src", "data")
    out = os.path.join(data, "tables") if a.ship else a.out
    if not os.path.isdir(out):
        os.makedirs(out)
    path = os.path.join(out, table["id"] + ".json")
    compat.save_json(path, table)
    print(table["id"], importer.counts(table), "->", os.path.normpath(path))
    if a.ship:
        compat.save_json(os.path.join(data, "default.json"),
                         {"active_table": table["id"]})


if __name__ == "__main__":
    main()
