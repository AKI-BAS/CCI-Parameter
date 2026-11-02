# -*- coding: utf-8 -*-
"""Text for the UI. The build writes the language of each extension into
lib/cci/lang.json (Icelandic for CCI-IS, English for CCI-EN)."""
from __future__ import unicode_literals

import os

from cci import compat

_HERE = os.path.dirname(os.path.abspath(__file__))
_TEXT = None


def load(path=None):
    global _TEXT
    _TEXT = compat.load_json(path or os.path.join(_HERE, "lang.json"))
    return _TEXT


def lang():
    if _TEXT is None:
        load()
    return _TEXT.get("_lang", "en")


def t(key, **params):
    if _TEXT is None:
        load()
    text = _TEXT.get(key)
    if text is None:
        return "[%s]" % key
    if params:
        try:
            return text.format(**params)
        except (KeyError, IndexError, ValueError):
            return text
    return text


def has(key):
    if _TEXT is None:
        load()
    return key in _TEXT
