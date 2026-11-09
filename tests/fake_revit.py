# -*- coding: utf-8 -*-
"""A tiny stand-in for the Revit API and pyRevit, just enough to run the
button scripts end to end in tests. It checks the tools' logic and wiring,
not Revit itself."""
import sys
import types


def _mod(name, **attrs):
    m = types.ModuleType(name)
    m.__dict__.update(attrs)
    sys.modules[name] = m
    return m


# ------------------------------------------------------------ .NET bits
class _Generic(object):
    def __getitem__(self, _t):
        return list


class Guid(object):
    def __init__(self, s):
        self.s = s


_mod("clr", GetClrType=lambda t: t, AddReference=lambda *a: None)
_mod("System", Guid=Guid, String=str, Int64=int, Enum=None)
_mod("System.Collections")
_mod("System.Collections.Generic", List=_Generic())


# ------------------------------------------------------------ Revit DB
class _Names(object):
    def __getattr__(self, name):
        if name.startswith("OST_"):
            return name
        raise AttributeError(name)


BuiltInCategory = _Names()


class ElementId(object):
    def __init__(self, v):
        self.Value = int(v)

    def __eq__(self, o):
        return isinstance(o, ElementId) and o.Value == self.Value

    def __hash__(self):
        return hash(self.Value)


ElementId.InvalidElementId = ElementId(-1)


class StorageType(object):
    String = "String"
    Integer = "Integer"


class Param(object):
    def __init__(self, name, value="", storage=StorageType.String):
        self.Definition = types.SimpleNamespace(Name=name)
        self.value = value
        self.StorageType = storage
        self.IsReadOnly = False

    def AsString(self):
        return self.value

    def AsValueString(self):
        return str(self.value)

    def AsInteger(self):
        return int(self.value)

    def Set(self, v):
        self.value = v


class Category(object):
    def __init__(self, bic, name=None):
        self.BuiltInCategory = bic
        self.Name = name or bic[4:]
        self.AllowsBoundParameters = True

    @staticmethod
    def GetCategory(doc, bic):
        return Category(bic)


class Element(object):
    _next = [1000]
    Name = types.SimpleNamespace(GetValue=lambda e: e._name)

    def __init__(self, bic, name="", params=None, etype=None, family="",
                 level=None, location=None):
        Element._next[0] += 1
        self.Id = ElementId(Element._next[0])
        self.UniqueId = "uid-%d" % Element._next[0]
        self.Category = Category(bic) if bic else None
        self._name = name
        self.FamilyName = family
        self.params = dict((p, Param(p, v)) for p, v in (params or {}).items())
        self.etype = etype
        self.Level = level
        self.Location = location
        self.Area = 10.0
        self.entities = {}
        self.is_type = False

    def LookupParameter(self, name):
        return self.params.get(name)

    def get_Parameter(self, bip):
        return None

    @property
    def Parameters(self):
        return list(self.params.values())

    def GetTypeId(self):
        return self.etype.Id if self.etype else ElementId.InvalidElementId

    def GetEntity(self, schema):
        return self.entities.get(id(schema))

    def SetEntity(self, entity):
        self.entities[id(entity.schema)] = entity


class FamilyInstance(Element):
    room = None
    to_room = None
    from_room = None
    StructuralMaterialType = "Concrete"

    @property
    def Room(self):
        return self.room

    def get_ToRoom(self, phase):
        return self.to_room

    def get_FromRoom(self, phase):
        return self.from_room


class Wall(Element):
    pass


class XYZ(tuple):
    def __new__(cls, x=0, y=0, z=0):
        return tuple.__new__(cls, (x, y, z))

    def __add__(self, o):
        return XYZ(*[a + b for a, b in zip(self, o)])


class LocationPoint(object):
    def __init__(self):
        self.Point = XYZ(0, 0, 0)


class Level(Element):
    def __init__(self, name, elev):
        Element.__init__(self, None, name)
        self.Name = name
        self.Elevation = elev


class Filter(object):
    def __init__(self, cats):
        self.cats = set(cats)


class FilteredElementCollector(object):
    def __init__(self, doc, view=None):
        self.items = list(doc.elements)

    def WherePasses(self, f):
        self.items = [e for e in self.items if e.Category and
                      e.Category.BuiltInCategory in f.cats]
        return self

    def WhereElementIsNotElementType(self):
        self.items = [e for e in self.items if not e.is_type]
        return self

    def OfClass(self, cls):
        self.items = [e for e in self.items if isinstance(e, cls)]
        return self

    def __iter__(self):
        return iter(self.items)


class _Generic2(object):
    """entity.Get[String](field) / entity.Set[String](field, value)"""

    def __init__(self, fn):
        self.fn = fn

    def __getitem__(self, _t):
        return self.fn


class Entity(object):
    def __init__(self, schema):
        self.schema = schema
        self.data = {}
        self.Get = _Generic2(lambda f: self.data.get(f, ""))
        self.Set = _Generic2(lambda f, v: self.data.__setitem__(f, v))

    def IsValid(self):
        return True


class Schema(object):
    _one = None

    @staticmethod
    def Lookup(guid):
        return Schema._one

    def GetField(self, name):
        return name


class SchemaBuilder(object):
    def __init__(self, guid):
        pass

    def __getattr__(self, name):
        return lambda *a: None

    def Finish(self):
        Schema._one = Schema()
        return Schema._one


class _AnyNS(object):
    def __getattr__(self, name):
        return name


_db = _mod("Autodesk.Revit.DB",
           BuiltInCategory=BuiltInCategory, ElementId=ElementId,
           ElementMulticategoryFilter=Filter,
           FamilyInstance=FamilyInstance,
           FilteredElementCollector=FilteredElementCollector,
           LocationPoint=LocationPoint, XYZ=XYZ, StorageType=StorageType, Wall=Wall,
           WallKind=_AnyNS(), Element=Element, Level=Level,
           BuiltInParameter=_AnyNS(), Category=Category,
           CategorySet=list, GroupTypeId=_AnyNS(), SpecTypeId=_AnyNS(),
           InstanceBinding=list, TypeBinding=list,
           SharedParameterElement=None,
           UnitUtils=types.SimpleNamespace(
               ConvertFromInternalUnits=lambda v, u: v * 0.3048),
           UnitTypeId=_AnyNS())
_mod("Autodesk")
_mod("Autodesk.Revit")
_mod("Autodesk.Revit.DB.ExtensibleStorage", AccessLevel=_AnyNS(),
     Entity=Entity, Schema=Schema, SchemaBuilder=SchemaBuilder)


# --------------------------------------------------------------- pyRevit
class Output(object):
    def __init__(self):
        self.lines = []

    def set_title(self, t):
        pass

    def print_md(self, text):
        self.lines.append(text)

    def print_table(self, rows, columns=None):
        self.lines.append(("table", columns, rows))

    def linkify(self, eid):
        return "<%s>" % eid.Value


class _Iter(object):
    def __init__(self, names):
        self.names = list(names)
        self.i = -1

    def Reset(self):
        self.i = -1

    def MoveNext(self):
        self.i += 1
        return self.i < len(self.names)

    @property
    def Key(self):
        return types.SimpleNamespace(Name=self.names[self.i])

    @property
    def Current(self):
        return None


class _Bindings(object):
    def __init__(self, doc):
        self.doc = doc

    def ForwardIterator(self):
        names = set()
        for e in self.doc.elements:
            names.update(n for n in e.params if n.startswith("CCI"))
        return _Iter(sorted(names))


class _Phases(list):
    @property
    def Size(self):
        return len(self)


class Doc(object):
    def __init__(self, elements):
        self.elements = elements
        self.IsFamilyDocument = False
        self.ProjectInformation = Element(None, "Project info")
        self.ProjectInformation.is_type = True
        self.Phases = _Phases(["Existing", "New Construction"])
        self.ParameterBindings = _Bindings(self)
        self.Application = None

    def GetElement(self, key):
        for e in self.elements:
            if e.UniqueId == key or e.Id == key:
                return e
        return None

    def GetRoomAtPoint(self, pt, phase=None):
        return None


STATE = {"doc": None, "alerts": [], "output": None, "selection": [],
         "confirm": True}


class Transaction(object):
    def __init__(self, name, doc=None):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class Dummy(object):
    def __init__(self):
        object.__setattr__(self, "Columns", [Dummy0() for _ in range(20)])
        object.__setattr__(self, "Items", Dummy0())
        object.__setattr__(self, "SelectedItems", [])
        object.__setattr__(self, "IsChecked", False)
        object.__setattr__(self, "Text", "")
        object.__setattr__(self, "SelectedIndex", -1)
        object.__setattr__(self, "SelectedItem", None)

    def __getattr__(self, name):
        return Dummy0()

    def __iadd__(self, handler):     # event += handler
        return self


class Dummy0(object):
    def __getattr__(self, name):
        return lambda *a, **k: None

    def __iadd__(self, handler):     # event += handler
        return self


class WPFWindow(object):
    def __init__(self, xaml):
        pass

    def __getattr__(self, name):
        d = Dummy()
        object.__setattr__(self, name, d)
        return d

    def ShowDialog(self):
        for handler in ("write_click", "save_click"):
            if hasattr(type(self), handler):
                getattr(self, handler)(None, None)
                return

    def Close(self):
        pass


def alert(msg, title=None, exitscript=False, yes=False, no=False, **k):
    STATE["alerts"].append(msg)
    if exitscript:
        raise SystemExit(msg)
    return STATE["confirm"] if yes else None


class Reactive(object):
    def OnPropertyChanged(self, name):
        pass


def _exit():
    raise SystemExit("script.exit")


def _get_output():
    STATE["output"] = Output()
    return STATE["output"]


class CommandSwitchWindow(object):
    @staticmethod
    def show(options, **k):
        return None


class SelectFromList(object):
    @staticmethod
    def show(items, **k):
        return None


forms = _mod("pyrevit.forms", alert=alert, WPFWindow=WPFWindow,
             Reactive=Reactive, reactive=property,
             pick_file=lambda **k: None, save_file=lambda **k: None,
             pick_folder=lambda **k: None,
             ask_for_string=lambda **k: None,
             CommandSwitchWindow=CommandSwitchWindow,
             SelectFromList=SelectFromList)
revit = _mod("pyrevit.revit", Transaction=Transaction,
             get_selection=lambda: types.SimpleNamespace(
                 elements=STATE["selection"]))
script = _mod("pyrevit.script", exit=_exit, get_output=_get_output,
              get_config=lambda *a: None, save_config=lambda: None,
              show_file_in_explorer=lambda p: None)
_mod("pyrevit", forms=forms, revit=revit, script=script)


class _DocProp(types.ModuleType):
    @property
    def doc(self):
        return STATE["doc"]


revit.__class__ = _DocProp
