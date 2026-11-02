# -*- coding: utf-8 -*-
"""Bind the CCI shared parameters, and move a project from one shared
parameter file to another (e.g. from CCI-tools' own file to Molio's C420)
without losing values.
"""
from __future__ import unicode_literals

from Autodesk.Revit.DB import (
    CategorySet, Category, FilteredElementCollector, GroupTypeId,
    InstanceBinding, SharedParameterElement, SpecTypeId, StorageType,
    TypeBinding)

from cci import formats, groups, sharedparams
from cci.revit import util


def kinds_for(key):
    return [k for k, keys in groups.PARAMS_BY_KIND.items() if key in keys]


def categories_for(key):
    kinds = kinds_for(key)
    out = []
    for cat in groups.all_categories():
        if groups.kind_of(cat) in kinds:
            out.append(cat)
    return out


def read_definitions(app, path):
    """{param name: ExternalDefinition} from a shared parameter file.

    Revit only opens the file set in its options, so it is swapped in for
    the read and put back afterwards.
    """
    original = app.SharedParametersFilename
    found = {}
    try:
        app.SharedParametersFilename = path
        dfile = app.OpenSharedParameterFile()
        if dfile is None:
            return None
        for group in dfile.Groups:
            for d in group.Definitions:
                found[d.Name] = d
    finally:
        app.SharedParametersFilename = original or ""
    return found


def find_definition(definitions, name):
    """Exact name, else a name that only differs in case
    (CCITopNode / CCITopnode)."""
    if name in definitions:
        return definitions[name]
    low = name.lower()
    for n, d in definitions.items():
        if n.lower() == low:
            return d
    return None


def _category_set(doc, names):
    cset = CategorySet()
    for b in util.bics(names):
        cat = Category.GetCategory(doc, b)
        if cat is None or not cat.AllowsBoundParameters:
            continue
        cset.Insert(cat)
    return cset


def _existing_binding(doc, name):
    low = name.lower()
    it = doc.ParameterBindings.ForwardIterator()
    it.Reset()
    while it.MoveNext():
        if it.Key.Name.lower() == low:
            return it.Key, it.Current
    return None


def shared_element(doc, definition):
    """SharedParameterElement behind a bound definition, or None for a
    plain project parameter."""
    try:
        el = doc.GetElement(definition.Id)
    except Exception:
        return None
    return el if isinstance(el, SharedParameterElement) else None


def bind_all(doc, definitions, keys):
    """Bind each key's parameter. Must run inside a Transaction.

    Report lists: added, updated, unchanged, missing, wrong_type, conflict
    (same name but a project parameter, or type/instance swapped) and
    other_file (same name from another shared parameter file: kept and
    used, and can be moved with migrate()).
    """
    report = {"added": [], "updated": [], "unchanged": [], "missing": [],
              "wrong_type": [], "conflict": [], "other_file": []}
    bindings = doc.ParameterBindings
    for key in keys:
        name = formats.PARAM[key]
        d = find_definition(definitions, name)
        if d is None:
            report["missing"].append(name)
            continue
        try:
            if d.GetDataType() != SpecTypeId.String.Text:
                report["wrong_type"].append(name)
                continue
        except AttributeError:
            pass
        wanted = _category_set(doc, categories_for(key))
        is_type = key.endswith("_t")
        existing = _existing_binding(doc, name)
        if existing is None:
            binding = TypeBinding(wanted) if is_type \
                else InstanceBinding(wanted)
            ok = bindings.Insert(d, binding, GroupTypeId.IdentityData)
            report["added" if ok else "wrong_type"].append(name)
            continue
        definition, binding = existing
        spe = shared_element(doc, definition)
        if spe is None or isinstance(binding, TypeBinding) != is_type:
            report["conflict"].append(name)
            continue
        if spe.GuidValue != d.GUID:
            report["other_file"].append(name)
        merged = binding.Categories
        changed = False
        for cat in wanted:
            if not merged.Contains(cat):
                merged.Insert(cat)
                changed = True
        if changed:
            binding.Categories = merged
            bindings.ReInsert(definition, binding, GroupTypeId.IdentityData)
            if name not in report["other_file"]:
                report["updated"].append(name)
        elif name not in report["other_file"]:
            report["unchanged"].append(name)
    return report


def _elements(doc, categories, types):
    for cat in categories:
        col = FilteredElementCollector(doc).OfCategoryId(cat.Id)
        col = col.WhereElementIsElementType() if types \
            else col.WhereElementIsNotElementType()
        for e in col:
            yield e


def migrate(doc, definitions, names):
    """Replace each named parameter with the one in `definitions`,
    keeping every value. Must run inside a Transaction.

    Returns {"moved": [(name, values)], "failed": [(name, error)]}.
    """
    out = {"moved": [], "failed": []}
    bindings = doc.ParameterBindings
    for name in names:
        existing = _existing_binding(doc, name)
        new_def = find_definition(definitions, name)
        if existing is None or new_def is None:
            continue
        old_def, binding = existing
        spe = shared_element(doc, old_def)
        if spe is None or spe.GuidValue == new_def.GUID:
            continue
        is_type = isinstance(binding, TypeBinding)
        cats = binding.Categories
        old_guid = spe.GuidValue
        values = []
        for e in _elements(doc, cats, is_type):
            p = e.get_Parameter(old_guid)
            if p is not None and p.StorageType == StorageType.String:
                v = p.AsString()
                if v:
                    values.append((e.Id, v))
        try:
            bindings.Remove(old_def)
            doc.Delete(spe.Id)
            new_binding = TypeBinding(cats) if is_type \
                else InstanceBinding(cats)
            if not bindings.Insert(new_def, new_binding,
                                   GroupTypeId.IdentityData):
                raise RuntimeError("Insert failed")
            for eid, v in values:
                p = doc.GetElement(eid).get_Parameter(new_def.GUID)
                if p is not None and not p.IsReadOnly:
                    p.Set(v)
        except Exception as ex:
            out["failed"].append((name, "%s" % ex))
            continue
        out["moved"].append((name, len(values)))
    return out


def bound_names(doc):
    names = set()
    it = doc.ParameterBindings.ForwardIterator()
    it.Reset()
    while it.MoveNext():
        names.add(it.Key.Name)
    return names


def source(doc):
    """Which shared parameter file the project's CCI parameters come from:
    'tool' (CCI-tools' own), 'other' (e.g. Molio's), 'mixed' or None."""
    names = dict((n.lower(), n) for n in formats.PARAM.values())
    kinds = set()
    it = doc.ParameterBindings.ForwardIterator()
    it.Reset()
    while it.MoveNext():
        name = names.get(it.Key.Name.lower())
        spe = shared_element(doc, it.Key) if name else None
        if spe is None:
            continue
        tool = sharedparams.is_tool_guid(name, spe.GuidValue)
        kinds.add("tool" if tool else "other")
    if not kinds:
        return None
    return kinds.pop() if len(kinds) == 1 else "mixed"
