# -*- coding: utf-8 -*-
"""Project settings and the numbering registry, stored in the Revit
project itself (Extensible Storage on Project Information), so they travel
with the .rvt and are the same for everyone on a central model."""
from __future__ import unicode_literals

import clr  # noqa: F401
from System import Guid, String
from Autodesk.Revit.DB.ExtensibleStorage import (
    AccessLevel, Entity, Schema, SchemaBuilder)

from cci import compat, numbering, settings as settings_mod

SCHEMA_GUID = Guid("dd2a37e4-5f35-4ff3-af22-8406561a2e79")
SCHEMA_NAME = "CCIToolsData"
F_SETTINGS = "Settings"
F_REGISTRY = "Registry"


def _schema():
    schema = Schema.Lookup(SCHEMA_GUID)
    if schema:
        return schema
    b = SchemaBuilder(SCHEMA_GUID)
    b.SetSchemaName(SCHEMA_NAME)
    b.SetReadAccessLevel(AccessLevel.Public)
    b.SetWriteAccessLevel(AccessLevel.Public)
    b.SetDocumentation("CCI tools: project settings and stable numbers")
    b.AddSimpleField(F_SETTINGS, clr.GetClrType(String))
    b.AddSimpleField(F_REGISTRY, clr.GetClrType(String))
    return b.Finish()


def _read(doc, field):
    schema = _schema()
    entity = doc.ProjectInformation.GetEntity(schema)
    if not entity or not entity.IsValid():
        return None
    value = entity.Get[String](schema.GetField(field))
    return compat.loads(value)


def _write(doc, field, data):
    """Must be called inside a Transaction."""
    schema = _schema()
    info = doc.ProjectInformation
    entity = info.GetEntity(schema)
    if not entity or not entity.IsValid():
        entity = Entity(schema)
    entity.Set[String](schema.GetField(field), compat.dumps(data))
    info.SetEntity(entity)


def load_settings(doc):
    return settings_mod.merged(_read(doc, F_SETTINGS))


def save_settings(doc, settings):
    _write(doc, F_SETTINGS, settings)


def load_registry(doc):
    return numbering.Registry(_read(doc, F_REGISTRY))


def save_registry(doc, registry):
    _write(doc, F_REGISTRY, registry.to_data())


def has_settings(doc):
    return _read(doc, F_SETTINGS) is not None
