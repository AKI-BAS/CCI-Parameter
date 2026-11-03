# -*- coding: utf-8 -*-
"""The tool's own shared parameter file, reading other files, and moving
a project from one file to another without losing values."""
import os
import sys
import types
import uuid

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, "..", "src", "lib"))
sys.path.insert(0, HERE)

import fake_revit as fr  # noqa: E402,F401  (fake Revit modules)
from cci import formats, sharedparams  # noqa: E402


def test_file_is_stable_and_complete(tmp_path):
    a = sharedparams.file_text()
    assert a == sharedparams.file_text()
    params = sharedparams.parse(a)
    assert set(params) == set(formats.PARAM[k] for k in sharedparams.KEYS)
    assert params["CCITopnode[Type]"]["datatype"] == "TEXT"
    assert params["CCIClassCode"]["guid"] == str(
        sharedparams.guid_for("CCIClassCode"))
    # known value, so a change of NAMESPACE can't slip through: models
    # made with an earlier copy of the tool must keep matching
    assert str(sharedparams.guid_for("CCIClassCode")) == str(uuid.uuid5(
        uuid.UUID("5d1b7f0e-3c39-4d55-9a4e-3a7c2c1e0c11"),
        "cci-tools:CCIClassCode"))
    path = sharedparams.write_file(str(tmp_path / "x.txt"))
    raw = open(path, "rb").read()
    assert raw[:2] == b"\xff\xfe"                   # UTF-16 LE BOM
    text = sharedparams.read_text(path)
    assert text == a
    info = sharedparams.check_file(text)
    assert info["tool_file"] and not info["missing"]


def test_check_other_file():
    molio_like = "\n".join([
        "*META\tVERSION\tMINVERSION", "META\t2\t1",
        "*GROUP\tID\tNAME", "GROUP\t1\tCCI",
        "PARAM\t%s\tCCIClassCode\tTEXT\t\t1\t1\t\t1\t0" % uuid.uuid4(),
        "PARAM\t%s\tCCITopNode\tTEXT\t\t1\t1\t\t1\t0" % uuid.uuid4(),
        "PARAM\t%s\tCCITypeID\tINTEGER\t\t1\t1\t\t1\t0" % uuid.uuid4(),
    ])
    info = sharedparams.check_file(molio_like)
    assert not info["tool_file"]
    assert info["case"] == {"CCITopnode": "CCITopNode"}
    assert info["not_text"] == ["CCITypeID"]
    assert "CCIFunctionalID" in info["missing"]
    assert "CCIClassification" not in info["missing"]   # optional


# --------------------------------------------- bind and migrate (fake API)

class _Guid(object):
    def __init__(self, s):
        self.s = str(s)

    def __eq__(self, o):
        return isinstance(o, _Guid) and o.s == self.s

    def __ne__(self, o):
        return not self == o

    def __str__(self):          # like System.Guid.ToString()
        return self.s


class _Def(object):
    _n = [0]

    def __init__(self, name, guid):
        self.Name = name
        self.GUID = _Guid(guid)
        _Def._n[0] += 1
        self.Id = "def%d" % _Def._n[0]

    def GetDataType(self):
        return "text"


class _SPE(object):
    def __init__(self, d):
        self.Id = d.Id
        self.GuidValue = d.GUID


class _Cats(list):
    def Insert(self, c):
        self.append(c)

    def Contains(self, c):
        return c in self


class _Binding(object):
    def __init__(self, cats):
        self.Categories = cats


class _TypeB(_Binding):
    pass


class _InstB(_Binding):
    pass


class _Param(object):
    StorageType = "String"
    IsReadOnly = False

    def __init__(self):
        self.v = ""

    def AsString(self):
        return self.v

    @property
    def HasValue(self):
        return bool(self.v)

    def Set(self, v):
        self.v = v


class _El(object):
    def __init__(self, cat, is_type):
        self.Id = id(self)
        self.cat = cat
        self.is_type = is_type
        self.params = {}

    def get_Parameter(self, key):
        guid = key.GUID if hasattr(key, "GUID") else key
        return self.params.get(guid.s)


class _It(object):
    def __init__(self, items):
        self.items = items
        self.i = -1

    def Reset(self):
        self.i = -1

    def MoveNext(self):
        self.i += 1
        return self.i < len(self.items)

    @property
    def Key(self):
        return self.items[self.i][0]

    @property
    def Current(self):
        return self.items[self.i][1]


class _Bindings(object):
    def __init__(self, doc):
        self.doc = doc
        self.map = []

    def ForwardIterator(self):
        return _It(list(self.map))

    def Insert(self, d, b, group):
        if any(k.Name == d.Name and k.GUID == d.GUID for k, _ in self.map):
            return False
        # project-side definition is its own object with an element id
        self.map.append((d, b))
        self.doc.spes[d.Id] = _SPE(d)
        for e in self.doc.elements:
            if e.cat in b.Categories and e.is_type == isinstance(b, _TypeB):
                e.params.setdefault(d.GUID.s, _Param())
        return True

    def ReInsert(self, d, b, group):
        return True

    def Remove(self, d):
        self.map = [(k, b) for k, b in self.map if k is not d]
        for e in self.doc.elements:
            e.params.pop(d.GUID.s, None)


class _Doc(object):
    def __init__(self, elements):
        self.elements = elements
        self.spes = {}
        self.ParameterBindings = _Bindings(self)

    def GetElement(self, key):
        if key in self.spes:
            return self.spes[key]
        for e in self.elements:
            if e.Id == key:
                return e
        return None

    def Delete(self, key):
        self.spes.pop(key, None)


class _Collector(object):
    def __init__(self, doc):
        self.doc = doc
        self.items = list(doc.elements)

    def OfCategoryId(self, cid):
        self.items = [e for e in self.items if e.cat == cid]
        return self

    def WhereElementIsElementType(self):
        self.items = [e for e in self.items if e.is_type]
        return self

    def WhereElementIsNotElementType(self):
        self.items = [e for e in self.items if not e.is_type]
        return self

    def __iter__(self):
        return iter(self.items)


class _Category(object):
    @staticmethod
    def GetCategory(doc, bic):
        return _CatObj(bic)


class _CatObj(object):
    def __init__(self, bic):
        self.Id = bic
        self.AllowsBoundParameters = True

    def __eq__(self, o):
        return getattr(o, "Id", o) == self.Id

    def __hash__(self):
        return hash(self.Id)


def _patch(monkeypatch):
    from cci.revit import params
    for name, value in dict(
            CategorySet=_Cats, Category=_Category,
            FilteredElementCollector=_Collector, TypeBinding=_TypeB,
            InstanceBinding=_InstB, SharedParameterElement=_SPE,
            GroupTypeId=types.SimpleNamespace(IdentityData="id"),
            SpecTypeId=types.SimpleNamespace(
                String=types.SimpleNamespace(Text="text")),
            StorageType=types.SimpleNamespace(String="String")).items():
        monkeypatch.setattr(params, name, value)
    return params


def _defs(guid_of):
    return dict((n, _Def(n, guid_of(n))) for n in formats.PARAM.values())


def test_bind_then_migrate_keeps_values(monkeypatch):
    params = _patch(monkeypatch)
    door_t = _El(_CatObj("OST_Doors"), True)
    door = _El(_CatObj("OST_Doors"), False)
    room = _El(_CatObj("OST_Rooms"), False)
    doc = _Doc([door_t, door, room])
    keys = list(formats.REQUIRED_PARAMS)

    tool = _defs(sharedparams.guid_for)
    rep = params.bind_all(doc, tool, keys)
    assert len(rep["added"]) == len(keys) and not rep["conflict"]
    assert params.source(doc) == "tool"

    g = lambda n: tool[n].GUID  # noqa: E731
    door_t.get_Parameter(g("CCIClassCode[Type]")).Set("QQC")
    door.get_Parameter(g("CCISingleLevelID")).Set("#QQC001")
    room.get_Parameter(g("CCIClassCode")).Set("AAB")
    assert door.get_Parameter(g("CCIClassCode[Type]")) is None  # type only

    molio = _defs(lambda n: uuid.uuid4())
    rep = params.bind_all(doc, molio, keys)
    assert sorted(rep["other_file"]) == sorted(formats.PARAM[k]
                                               for k in keys)
    moved = params.migrate(doc, molio, rep["other_file"])
    assert not moved["failed"]
    counts = dict(moved["moved"])
    assert counts["CCIClassCode[Type]"] == 1
    assert counts["CCIClassCode"] == 1
    m = lambda n: molio[n].GUID  # noqa: E731
    assert door_t.get_Parameter(m("CCIClassCode[Type]")).AsString() == "QQC"
    assert door.get_Parameter(m("CCISingleLevelID")).AsString() == "#QQC001"
    assert room.get_Parameter(m("CCIClassCode")).AsString() == "AAB"
    assert door.get_Parameter(g("CCISingleLevelID")) is None   # old gone
    assert params.source(doc) == "other"
    # running again changes nothing
    rep = params.bind_all(doc, molio, keys)
    assert not rep["other_file"] and not rep["added"]


def test_case_only_difference_is_the_same_parameter(monkeypatch):
    params = _patch(monkeypatch)
    doc = _Doc([_El(_CatObj("OST_Doors"), True)])
    molio = _defs(lambda n: uuid.uuid4())
    molio["CCITopNode[Type]"] = molio.pop("CCITopnode[Type]")
    molio["CCITopNode[Type]"].Name = "CCITopNode[Type]"
    rep = params.bind_all(doc, molio, ["topnode_t"])
    assert rep["added"] == ["CCITopnode[Type]"]
    from cci.revit import util
    util.use_project_names(doc)
    assert util.name_for("topnode_t") == "CCITopNode[Type]"
    util._ACTUAL.clear()


def test_leftovers(monkeypatch):
    params = _patch(monkeypatch)
    win_t = _El(_CatObj("OST_Windows"), True)
    win_t2 = _El(_CatObj("OST_Windows"), True)
    doc = _Doc([win_t, win_t2])
    defs = _defs(sharedparams.guid_for)
    params.bind_all(doc, defs, ["type_id_t"])
    old = _Def("CCITypeID_Type", uuid.uuid4())
    old2 = _Def("CCSClassCode", uuid.uuid4())
    doc.ParameterBindings.Insert(old, _TypeB(_Cats([_CatObj("OST_Windows")])),
                                 "id")
    doc.ParameterBindings.Insert(old2, _InstB(_Cats([_CatObj("OST_Windows")])),
                                 "id")
    win_t.get_Parameter(old.GUID).Set("%QQA1")
    found = params.leftovers(doc)
    assert [(f["name"], f["is_type"], f["values"]) for f in found] == [
        ("CCITypeID_Type", True, 1), ("CCSClassCode", False, 0)]


def test_migrate_failure_raises_so_the_move_rolls_back(monkeypatch):
    params = _patch(monkeypatch)
    door_t = _El(_CatObj("OST_Doors"), True)
    doc = _Doc([door_t])
    tool = _defs(sharedparams.guid_for)
    params.bind_all(doc, tool, ["class_t"])
    molio = _defs(lambda n: uuid.uuid4())
    monkeypatch.setattr(_Bindings, "Insert", lambda self, d, b, g: False)
    import pytest
    with pytest.raises(params.MigrationError):
        params.migrate(doc, molio, ["CCIClassCode[Type]"])
