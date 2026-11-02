# -*- coding: utf-8 -*-
"""Small helpers so the same code runs on IronPython 2.7 and CPython 3."""
from __future__ import unicode_literals

import io
import json
import sys

PY2 = sys.version_info[0] == 2

if PY2:  # pragma: no cover - IronPython / Python 2 only
    text_type = unicode  # noqa: F821
    string_types = (str, unicode)  # noqa: F821
else:
    text_type = str
    string_types = (str,)


def to_text(value):
    """Return value as text; None stays None."""
    if value is None:
        return None
    if isinstance(value, text_type):
        return value
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return text_type(value)


def load_json(path):
    with io.open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def save_json(path, data):
    text = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)
    with io.open(path, "w", encoding="utf-8") as f:
        f.write(to_text(text))


def dumps(data):
    return to_text(json.dumps(data, ensure_ascii=False, sort_keys=True))


def loads(text):
    if not text:
        return None
    return json.loads(text)
