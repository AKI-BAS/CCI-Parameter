# -*- coding: utf-8 -*-
"""Build and validate CCI codes as described in BIM Ísland,
"CCI leiðbeiningar", útgáfa 2 (11.01.2023).

    CCITopnode                 [L]
    CCIClassCode               X / XX / XXX              e.g. QQC, AD, ULD
    CCITypeID                  %XXXaaa                   e.g. %QQC001, %QQC01.001
    CCIMultiLevelTypeID        §U.VV.XXXbbb              e.g. §B.AD.QQC001
    CCIFunctionalID            =Ukk.VVmm.WWnn.XXXppp     e.g. =H01.HD02.EGC001
    CCIMultiLevelLocationID    Bxx.yy.zzz                e.g. B01.01.001 (no prefix)
    CCISingleLevelID           #XXXccc                   e.g. #QQC001
    CCISingleLevelLocationAtID +Bxx.yy.zzz               e.g. +B01.K1.051

Validators return None when the value is fine, otherwise an issue key
(see lang/*.json, "fmt.*") that the UI translates.
"""
from __future__ import unicode_literals

import re

# Domains (klasar), "tæmandi listi" in CCI leiðbeiningar v2, kafli 1.
TOPNODES = ("C", "E", "S", "Z", "B", "A", "L", "R", "D", "P", "G", "U")

PARAM = {
    "class": "CCIClassCode",
    "class_t": "CCIClassCode[Type]",
    "topnode": "CCITopnode",
    "topnode_t": "CCITopnode[Type]",
    "type_id": "CCITypeID",
    "type_id_t": "CCITypeID[Type]",
    "ml_type_id": "CCIMultiLevelTypeID",
    "functional_id": "CCIFunctionalID",
    "ml_location_id": "CCIMultiLevelLocationID",
    "single_id": "CCISingleLevelID",
    "location_at_id": "CCISingleLevelLocationAtID",
    # Not in BIM Ísland's list of 11, but the IFC export's
    # "Classification field name" points at it.
    "classification": "CCIClassification",
    "classification_t": "CCIClassification[Type]",
    # Not BIM Ísland parameters, but many templates have them (Molio's
    # file): written when the project has them, never added.
    "class_name": "CCIClassName",
    "class_name_t": "CCIClassName[Type]",
    "class_version": "CCIClassCodeVersion",
    "class_version_t": "CCIClassCodeVersion[Type]",
}

# The 11 parameters BIM Ísland requires (CCI leiðbeiningar fyrir Revit).
REQUIRED_PARAMS = (
    "class", "class_t", "functional_id", "ml_location_id", "ml_type_id",
    "single_id", "location_at_id", "topnode", "topnode_t", "type_id",
    "type_id_t",
)
OPTIONAL_PARAMS = ("classification", "classification_t")

_CLASS_RE = re.compile(r"^[A-Z]{1,3}$")
_TOPNODE_RE = re.compile(r"^\[([A-Z])\]$")
_LEVEL_RE = re.compile(r"^(\d{2}|K\d{1,2}|M\d{1,2})$")
_LOC_RE = re.compile(r"^B(\d{2})\.(\d{2}|K\d{1,2}|M\d{1,2})\.(\d{3})$")
_TYPE_RE = re.compile(r"^(\[[A-Z]\])?%([A-Z]{1,3})(\d{1,3})(\.\d{1,3})?$")
_ML_TYPE_RE = re.compile(
    r"^(\[[A-Z]\])?§([A-Z])\.([A-Z]{2})\.([A-Z]{3})(\d{1,3})(\.\d{1,3})?$")
_SINGLE_RE = re.compile(r"^(\[[A-Z]\])?#([A-Z]{1,3})(\d{1,4})$")
# =Ukk[.VVmm][.WWnn].XXXppp - the feeding system (VVmm) may be left out.
_FUNC_RE = re.compile(
    r"^(\[[A-Z]\])?=([A-Z])(\d{2})(\.[A-Z]{2}\d{2}){0,2}\.([A-Z]{3})(\d{3})$")


def _pad(n, width):
    n = int(n)
    if n < 0:
        raise ValueError("negative number")
    return ("%0" + str(int(width)) + "d") % n


def norm(value):
    """Strip and upper-case a code typed by a person ('qqc ' -> 'QQC')."""
    if value is None:
        return ""
    return value.strip().upper()


# ---------------------------------------------------------------- builders

def topnode(letter):
    letter = norm(letter).strip("[]")
    if letter not in TOPNODES:
        raise ValueError("unknown topnode %s" % letter)
    return "[%s]" % letter


def type_id(class_code, number, pad=3, sub=None, sub_pad=3,
            with_topnode=None):
    """%QQC001, or %QQC01.001 with a subtype number."""
    class_code = norm(class_code)
    if not _CLASS_RE.match(class_code):
        raise ValueError("bad class code %s" % class_code)
    if sub is None:
        body = "%" + class_code + _pad(number, pad)
    else:
        body = "%" + class_code + _pad(number, 2) + "." + _pad(sub, sub_pad)
    return (topnode(with_topnode) if with_topnode else "") + body


def ml_type_id(u, vv, xxx, number, pad=3, sub=None, sub_pad=3,
               with_topnode=None):
    """§B.AD.QQC001"""
    u, vv, xxx = norm(u), norm(vv), norm(xxx)
    if not re.match(r"^[A-Z]$", u):
        raise ValueError("bad functional system %s" % u)
    if not re.match(r"^[A-Z]{2}$", vv):
        raise ValueError("bad technical system %s" % vv)
    if not re.match(r"^[A-Z]{3}$", xxx):
        raise ValueError("bad component %s" % xxx)
    if sub is None:
        num = _pad(number, pad)
    else:
        num = _pad(number, 2) + "." + _pad(sub, sub_pad)
    body = "§%s.%s.%s%s" % (u, vv, xxx, num)
    return (topnode(with_topnode) if with_topnode else "") + body


def single_id(class_code, number, pad=3, with_topnode=None):
    """#QQC001"""
    class_code = norm(class_code)
    if not _CLASS_RE.match(class_code):
        raise ValueError("bad class code %s" % class_code)
    body = "#" + class_code + _pad(number, pad)
    return (topnode(with_topnode) if with_topnode else "") + body


def location_id(building, level_code, room, building_pad=2, room_pad=3):
    """B01.01.001 - BIM Ísland's room number (no prefix)."""
    level_code = norm(level_code)
    if not _LEVEL_RE.match(level_code):
        raise ValueError("bad level code %s" % level_code)
    return "B%s.%s.%s" % (_pad(building, building_pad), level_code,
                          _pad(room, room_pad))


def location_at_id(building, level_code, room, building_pad=2, room_pad=3):
    """+B01.01.001"""
    return "+" + location_id(building, level_code, room, building_pad,
                             room_pad)


def classification(class_code, description=None):
    """Value for CCIClassification: 'AD' or 'AD:Wall construction'.

    Revit's IFC exporter reads this field as
    [ClassificationName]Code:Description, so a leading bracket would be
    taken as the name of the classification system: '[L]AD' would export
    as a classification called 'L' with the code 'AD'. No brackets here;
    the system name comes from IFC Classification Settings and the topnode
    has its own parameter (CCITopnode), as BIM Ísland's IDS expects.
    """
    class_code = norm(class_code)
    if not class_code:
        return ""
    description = (description or "").replace(":", " ").strip()
    if description:
        return "%s:%s" % (class_code, description)
    return class_code


_CLS_RE = re.compile(r"^((?:\[[^\]]*\])*)([A-Z]{1,3})(:.*)?$")


def code_of_classification(value):
    """'AD' from 'AD', 'AD:Wall construction' or '[CCI][L]AD:...'."""
    m = _CLS_RE.match((value or "").strip())
    return m.group(2) if m else None


def classification_prefix(value):
    """The bracket part Revit takes as the classification name, if any:
    '[CCI][L]AD' -> 'CCI', '[L]AD' -> 'L', 'AD' -> None."""
    m = re.match(r"^\[([^\]]*)\]", (value or "").strip())
    return m.group(1) if m else None


# -------------------------------------------------------------- validators

def check_class(value):
    value = value or ""
    if not value:
        return "fmt.empty"
    if not _CLASS_RE.match(value):
        return "fmt.class_code"
    return None


def check_topnode(value):
    value = value or ""
    if not value:
        return "fmt.empty"
    m = _TOPNODE_RE.match(value)
    if not m or m.group(1) not in TOPNODES:
        return "fmt.topnode"
    return None


def check_type_id(value):
    if not value:
        return "fmt.empty"
    return None if _TYPE_RE.match(value) else "fmt.type_id"


def check_ml_type_id(value):
    if not value:
        return "fmt.empty"
    return None if _ML_TYPE_RE.match(value) else "fmt.ml_type_id"


def check_single_id(value):
    if not value:
        return "fmt.empty"
    return None if _SINGLE_RE.match(value) else "fmt.single_id"


def check_functional_id(value):
    if not value:
        return "fmt.empty"
    return None if _FUNC_RE.match(value) else "fmt.functional_id"


def check_location_id(value):
    if not value:
        return "fmt.empty"
    if value.startswith("+"):
        # BIM Ísland: do not use the + prefix on room numbers.
        return "fmt.location_plus"
    return None if _LOC_RE.match(value) else "fmt.location_id"


def check_location_at_id(value):
    if not value:
        return "fmt.empty"
    if not value.startswith("+"):
        return "fmt.location_at_prefix"
    return None if _LOC_RE.match(value[1:]) else "fmt.location_id"


def check_level_code(value):
    return None if _LEVEL_RE.match(value or "") else "fmt.level_code"


def check_classification(value):
    if not value:
        return "fmt.empty"
    if code_of_classification(value) is None:
        return "fmt.classification"
    return None


VALIDATORS = {
    "class": check_class,
    "class_t": check_class,
    "topnode": check_topnode,
    "topnode_t": check_topnode,
    "type_id": check_type_id,
    "type_id_t": check_type_id,
    "ml_type_id": check_ml_type_id,
    "functional_id": check_functional_id,
    "ml_location_id": check_location_id,
    "single_id": check_single_id,
    "location_at_id": check_location_at_id,
    "classification": check_classification,
    "classification_t": check_classification,
}


# ---------------------------------------------------------------- parsing

def class_of_id(value):
    """Class code inside a type/single/multilevel ID, or None."""
    if not value:
        return None
    for rx, group in ((_TYPE_RE, 2), (_SINGLE_RE, 2), (_ML_TYPE_RE, 4)):
        m = rx.match(value)
        if m:
            return m.group(group)
    m = _FUNC_RE.match(value)
    if m:
        return m.group(5)
    return None


def number_of_id(value):
    """Running number in %QQC001 / #QQC001 / §B.AD.QQC001, or None."""
    if not value:
        return None
    m = _TYPE_RE.match(value)
    if m:
        return int(m.group(3))
    m = _SINGLE_RE.match(value)
    if m:
        return int(m.group(3))
    m = _ML_TYPE_RE.match(value)
    if m:
        return int(m.group(5))
    return None


def has_subtype(value, class_code):
    """True for a valid hand-made subtype ID of this class, e.g.
    %QQC01.001 or §B.AD.QQC01.001. Those are kept as they are."""
    if not value or class_of_id(value) != class_code:
        return False
    m = _TYPE_RE.match(value) or _ML_TYPE_RE.match(value)
    return bool(m and m.group(m.lastindex) and
                m.group(m.lastindex).startswith("."))
