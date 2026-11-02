# -*- coding: utf-8 -*-
"""Reading and writing Revit elements for the CCI buttons."""
from __future__ import unicode_literals

import os

import clr  # noqa: F401  (loads the .NET bridge)
from System.Collections.Generic import List
from Autodesk.Revit.DB import (
    BuiltInCategory, ElementId, ElementMulticategoryFilter,
    FamilyInstance, FilteredElementCollector, LocationPoint, StorageType,
    Wall, WallKind)

from cci import compat, formats, groups
from cci.store import Store

_LIB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.normpath(os.path.join(_LIB, "..", "..", "data"))


# ----------------------------------------------------------------- basics

def eid(element_or_id):
    """Element id as int (Revit 2024+ uses .Value, older .IntegerValue)."""
    i = element_or_id if isinstance(element_or_id, ElementId) \
        else element_or_id.Id
    try:
        return int(i.Value)
    except AttributeError:  # pragma: no cover - Revit < 2024
        return int(i.IntegerValue)


def bic_name(element):
    cat = element.Category
    if cat is None:
        return None
    try:
        return str(cat.BuiltInCategory)
    except AttributeError:  # pragma: no cover - Revit < 2023
        return str(System_Enum_name(cat.Id))


def System_Enum_name(cat_id):  # pragma: no cover - Revit < 2023
    from System import Enum
    return Enum.GetName(BuiltInCategory, cat_id.IntegerValue)


def bics(names):
    out = []
    for n in names:
        b = getattr(BuiltInCategory, n, None)
        if b is not None:
            out.append(b)
    return out


def instances(doc, category_names, view_id=None):
    cats = bics(category_names)
    if not cats:
        return []
    f = ElementMulticategoryFilter(List[BuiltInCategory](cats))
    col = FilteredElementCollector(doc, view_id) if view_id \
        else FilteredElementCollector(doc)
    return [e for e in col.WherePasses(f).WhereElementIsNotElementType()
            if e.Category is not None]


def element_type(doc, element):
    tid = element.GetTypeId()
    if tid is None or tid == ElementId.InvalidElementId:
        return None
    return doc.GetElement(tid)


def family_name(etype):
    if etype is None:
        return ""
    try:
        return etype.FamilyName or ""
    except AttributeError:
        return ""


def type_name(etype):
    if etype is None:
        return ""
    try:
        from Autodesk.Revit.DB import Element
        return Element.Name.GetValue(etype) or ""
    except Exception:
        return getattr(etype, "Name", "") or ""


def label(doc, element):
    etype = element_type(doc, element)
    cat = element.Category.Name if element.Category else "?"
    if etype is None:
        name = get(element, "Name") or ""
        number = get(element, "Number") or ""
        return "%s: %s %s" % (cat, number, name)
    return "%s: %s : %s" % (cat, family_name(etype), type_name(etype))


# -------------------------------------------------------------- parameters

# key -> the name the open project actually uses, when it differs from
# BIM Ísland's spelling only in case (e.g. CCITopNode vs CCITopnode).
_ACTUAL = {}


def use_project_names(doc):
    _ACTUAL.clear()
    try:
        it = doc.ParameterBindings.ForwardIterator()
    except Exception:
        return
    want = dict((n.lower(), k) for k, n in formats.PARAM.items())
    it.Reset()
    while it.MoveNext():
        name = it.Key.Name
        key = want.get(name.lower())
        if key and name != formats.PARAM[key]:
            _ACTUAL[key] = name


def name_for(key):
    return _ACTUAL.get(key, formats.PARAM[key])


def get(element, name):
    """Text value of a parameter by name, '' if empty, None if missing."""
    if element is None:
        return None
    p = element.LookupParameter(name)
    if p is None:
        return None
    if p.StorageType == StorageType.String:
        return compat.to_text(p.AsString() or "")
    return compat.to_text(p.AsValueString() or "")


def get_key(element, key):
    return get(element, name_for(key))


def has_key(element, key):
    return element is not None and \
        element.LookupParameter(name_for(key)) is not None


def set_key(element, key, value):
    """Set a CCI text parameter. Returns True if the value changed."""
    p = element.LookupParameter(name_for(key))
    if p is None or p.IsReadOnly or p.StorageType != StorageType.String:
        return False
    old = p.AsString() or ""
    value = value or ""
    if old == value:
        return False
    p.Set(value)
    return True


# --------------------------------------------------------------- facts

def facts(doc, element, etype=None):
    """What the mapping rules look at (see cci.rules)."""
    if etype is None:
        etype = element_type(doc, element)
    f = {"category": bic_name(element),
         "family": family_name(etype),
         "type": type_name(etype),
         "params": {}}
    if etype is None:
        f["type"] = get(element, "Name") or ""
    for src in (etype, element):
        if src is None:
            continue
        for p in src.Parameters:
            try:
                name = p.Definition.Name
                if name.startswith("CCI"):
                    continue
                if p.StorageType == StorageType.String:
                    v = p.AsString()
                else:
                    v = p.AsValueString()
                if v is not None and name not in f["params"]:
                    f["params"][name] = compat.to_text(v)
            except Exception:
                continue
    if isinstance(element, Wall):
        try:
            f["params"]["Function"] = str(element.WallType.Function)
            f["curtain"] = element.WallType.Kind == WallKind.Curtain
        except Exception:
            pass
    f["structural"] = _structural(element)
    if isinstance(element, FamilyInstance):
        try:
            f["material"] = str(element.StructuralMaterialType)
        except Exception:
            pass
    return f


def exported_to_ifc(element, etype=None):
    """False when the element (or its type) is set not to export to IFC:
    'Export to IFC' = Don't Export, or IfcExportAs = DontExport."""
    for src in (element, etype):
        if src is None:
            continue
        v = get(src, "IfcExportAs") or get(src, "Export Type to IFC As") or ""
        if v.replace(" ", "").lower().startswith("dontexport"):
            return False
    inst = _int_param(element, "IFC_EXPORT_ELEMENT")
    if inst == 2:
        return False
    if inst in (0, None) and etype is not None:
        if _int_param(etype, "IFC_EXPORT_ELEMENT_TYPE") == 2:
            return False
    return True


def _int_param(element, bip_name):
    from Autodesk.Revit.DB import BuiltInParameter
    b = getattr(BuiltInParameter, bip_name, None)
    if b is None or element is None:
        return None
    try:
        p = element.get_Parameter(b)
        return p.AsInteger() if p is not None and p.HasValue else None
    except Exception:
        return None


def _structural(element):
    from Autodesk.Revit.DB import BuiltInParameter
    for bip in ("WALL_STRUCTURAL_SIGNIFICANT", "FLOOR_PARAM_IS_STRUCTURAL"):
        b = getattr(BuiltInParameter, bip, None)
        if b is None:
            continue
        p = element.get_Parameter(b)
        if p is not None:
            return p.AsInteger() == 1
    return bic_name(element) in ("OST_StructuralColumns",
                                 "OST_StructuralFraming",
                                 "OST_StructuralFoundation")


# ------------------------------------------------------------------- data

def data_folder():
    """Studio data folder: pyRevit setting, else %APPDATA%\\CCI-tools."""
    path = ""
    try:
        from pyrevit import script
        cfg = script.get_config("CCI")
        if cfg is not None:
            path = cfg.get_option("data_folder", "") or ""
    except Exception:
        path = ""
    if not path:
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        path = os.path.join(base, "CCI-tools")
    return path


def set_data_folder(path):
    from pyrevit import script
    cfg = script.get_config("CCI")
    cfg.data_folder = path or ""
    script.save_config()


def store():
    return Store(DATA_DIR, data_folder())


def load_rules(settings):
    return store().ruleset({
        "element": settings["topnode_elements"],
        "system": settings["topnode_elements"],
        "space": settings["topnode_spaces"]})


def load_classes():
    return store().load_table()


def used_codes(doc):
    """{(topnode letter, code): count} of classes used in the model."""
    out = {}
    for e in classified_instances(doc):
        etype = element_type(doc, e)
        code = get_key(e, "class") or get_key(etype, "class_t") or ""
        if not code:
            continue
        tn = get_key(e, "topnode") or get_key(etype, "topnode_t") or ""
        if not tn:
            tn = "[B]" if groups.kind_of(bic_name(e)) == "space" else "[L]"
        key = (tn.strip("[]"), code)
        out[key] = out.get(key, 0) + 1
    return out


def is_placed_space(element):
    try:
        return element.Area > 0 and element.Location is not None
    except AttributeError:
        return True


def point_of(element):
    loc = element.Location
    if isinstance(loc, LocationPoint):
        return loc.Point
    return None


def classified_instances(doc):
    """All instances in categories the tool handles, rooms included
    (unplaced/unenclosed rooms left out)."""
    out = []
    for e in instances(doc, groups.all_categories()):
        if groups.kind_of(bic_name(e)) == "space" and \
                not is_placed_space(e):
            continue
        out.append(e)
    return out


def group_and_kind(doc, element):
    cat = bic_name(element)
    kind = groups.kind_of(cat)
    f = {"category": cat, "structural": _structural(element)}
    if isinstance(element, Wall):
        try:
            f["curtain"] = element.WallType.Kind == WallKind.Curtain
        except Exception:
            pass
    if isinstance(element, FamilyInstance):
        try:
            f["material"] = str(element.StructuralMaterialType)
        except Exception:
            pass
    return groups.group_of(f), kind
