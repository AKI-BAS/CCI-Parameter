# -*- coding: utf-8 -*-
"""Element groups from "Þróunarstig byggingarhluta" (DiKon/BIM7AA/Molio,
REV4, Icelandic translation by BIM Ísland), their Revit categories, and
which CCI parameters each kind of element should carry.
"""
from __future__ import unicode_literals

# group id -> Revit categories (BuiltInCategory names). Order matters only
# for display. Walls, floors, columns and framing are split further in
# group_of() by structural flag / material.
GROUPS = [
    ("light_walls", ["OST_Walls"]),
    ("curtain_walls", ["OST_CurtainWallPanels", "OST_CurtainWallMullions"]),
    ("windows", ["OST_Windows"]),
    ("doors", ["OST_Doors"]),
    ("floors", ["OST_Floors"]),
    ("ceilings", ["OST_Ceilings"]),
    ("stairs", ["OST_Stairs", "OST_StairsRuns", "OST_StairsLandings",
                "OST_Ramps"]),
    ("railings", ["OST_StairsRailing", "OST_Railings"]),
    ("roofs", ["OST_Roofs"]),
    ("casework", ["OST_Casework"]),
    ("spaces", ["OST_Rooms", "OST_MEPSpaces", "OST_Areas"]),
    ("foundations", ["OST_StructuralFoundation"]),
    ("concrete_walls", []),
    ("concrete_columns", ["OST_StructuralColumns"]),
    ("steel_columns", []),
    ("concrete_slabs", []),
    ("concrete_beams", ["OST_StructuralFraming"]),
    ("steel_beams", []),
    ("cable_routes", ["OST_CableTray", "OST_CableTrayFitting", "OST_Conduit",
                      "OST_ConduitFitting"]),
    ("electrical", ["OST_ElectricalEquipment", "OST_ElectricalFixtures",
                    "OST_LightingFixtures", "OST_LightingDevices",
                    "OST_CommunicationDevices", "OST_DataDevices",
                    "OST_FireAlarmDevices", "OST_SecurityDevices",
                    "OST_NurseCallDevices", "OST_TelephoneDevices"]),
    ("ducts", ["OST_DuctCurves", "OST_DuctFitting", "OST_FlexDuctCurves",
               "OST_DuctInsulations"]),
    ("ventilation", ["OST_MechanicalEquipment", "OST_DuctTerminal",
                     "OST_DuctAccessory"]),
    ("pipes", ["OST_PipeCurves", "OST_PipeFitting", "OST_FlexPipeCurves",
               "OST_PipeInsulations"]),
    ("plumbing", ["OST_PlumbingFixtures", "OST_PipeAccessory",
                  "OST_Sprinklers"]),
    ("openings", ["OST_ShaftOpening", "OST_SWallRectOpening",
                  "OST_FloorOpening", "OST_RoofOpening",
                  "OST_StructuralFramingOpening", "OST_ColumnOpening"]),
    ("site_surface", ["OST_Topography", "OST_Toposolid", "OST_Hardscape"]),
    ("planting", ["OST_Planting"]),
    ("site_walls", []),
    ("site_furniture", ["OST_Site"]),
]
GROUP_IDS = [g for g, _ in GROUPS]

# Categories that are part of building systems and get CCIFunctionalID.
SYSTEM_CATEGORIES = set(
    dict(GROUPS)["cable_routes"] + dict(GROUPS)["electrical"]
    + dict(GROUPS)["ducts"] + dict(GROUPS)["ventilation"]
    + dict(GROUPS)["pipes"] + dict(GROUPS)["plumbing"])
SPACE_CATEGORIES = set(dict(GROUPS)["spaces"])

# Extra categories that are classified but are in no LOD group.
EXTRA_CATEGORIES = ["OST_Furniture", "OST_FurnitureSystems",
                    "OST_SpecialityEquipment", "OST_GenericModel",
                    "OST_Columns", "OST_Parking", "OST_Entourage"]


def all_categories():
    cats = []
    for _, c in GROUPS:
        for x in c:
            if x not in cats:
                cats.append(x)
    for x in EXTRA_CATEGORIES:
        if x not in cats:
            cats.append(x)
    return cats


def kind_of(category):
    """'space', 'system' or 'element'."""
    if category in SPACE_CATEGORIES:
        return "space"
    if category in SYSTEM_CATEGORIES:
        return "system"
    return "element"


def group_of(facts):
    """LOD group for an element, or None.

    facts: dict with 'category', optional 'structural' (bool),
    'curtain' (bool, curtain/stacked system wall), 'material' ('Concrete',
    'Steel', ... the structural material class).
    """
    cat = facts.get("category")
    structural = bool(facts.get("structural"))
    material = (facts.get("material") or "").lower()
    if cat == "OST_Walls":
        if facts.get("curtain"):
            return "curtain_walls"
        return "concrete_walls" if structural else "light_walls"
    if cat == "OST_Floors":
        return "concrete_slabs" if structural else "floors"
    if cat == "OST_StructuralColumns":
        return "steel_columns" if material == "steel" else "concrete_columns"
    if cat == "OST_StructuralFraming":
        return "steel_beams" if material == "steel" else "concrete_beams"
    for gid, cats in GROUPS:
        if cat in cats:
            return gid
    return None


# Which parameters each kind of element carries (Revit guide, bls. 2).
PARAMS_BY_KIND = {
    "element": ["class", "class_t", "topnode", "topnode_t", "type_id",
                "type_id_t", "ml_type_id", "single_id", "location_at_id",
                "classification", "classification_t"],
    "system": ["class", "class_t", "topnode", "topnode_t", "type_id",
               "type_id_t", "ml_type_id", "single_id", "location_at_id",
               "functional_id", "classification", "classification_t"],
    "space": ["class", "topnode", "ml_location_id", "classification"],
}

# Scope (page 1 of CCI leiðbeiningar v2) -> what it requires.
SCOPES = ["coordination", "systems", "operations", "product_id",
          "location_id"]
SCOPE_FIELDS = {
    "coordination": ["class", "type_id"],
    "systems": ["class", "functional_id"],
    "operations": ["topnode", "class", "ml_type_id", "ml_location_id"],
    "product_id": ["single_id"],
    "location_id": ["location_at_id"],
}
# Fields that are about classification (9.1 Flokkun), gated by LOD.
CLASSIFICATION_FIELDS = ("class", "type_id", "topnode", "ml_type_id")
LODS = (200, 300, 325, 400)


def min_lod_for_classification(group):
    # Úrtök og opnanir only get class + type ID from LOD 325.
    return 325 if group == "openings" else 300


def required_fields(kind, group, lod, scopes):
    """Logical fields (class, type_id, ...) required on one element.

    'class' means: CCIClassCode or CCIClassCode[Type] (instance wins), and
    the same for topnode/type_id.
    """
    allowed = set(f[:-2] if f.endswith("_t") else f
                  for f in PARAMS_BY_KIND[kind])
    need = []
    for scope in scopes:
        for f in SCOPE_FIELDS.get(scope, []):
            if f in allowed and f not in need:
                need.append(f)
    if group is not None and lod is not None:
        gate = min_lod_for_classification(group)
        if lod < gate:
            need = [f for f in need if f not in CLASSIFICATION_FIELDS]
        # Úrtök og opnanir, LOD 400: "Einstakt auðkenni".
        if group == "openings" and lod >= 400 and "single_id" not in need:
            need.append("single_id")
    if kind == "space":
        # Spaces have no types in Revit.
        need = [f for f in need if f not in ("type_id", "ml_type_id")]
    return need
