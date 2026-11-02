# -*- coding: utf-8 -*-
"""IFC export support: the user-defined property set file
(CCI_in_Revit_to_IFC.txt, as in "CCI leiðbeiningar fyrir Revit" bls. 4)
and the Classification Settings values.
"""
from __future__ import unicode_literals

from cci import formats

PSET_NAME = "CCI_Administrative"

# IFC property name -> Revit parameters, type parameter first so the
# instance value (listed last) wins when both are filled, matching
# BIM Ísland's file.
_ORDER = [
    ("CCITopnode", ["topnode_t", "topnode"]),
    ("CCIClassCode", ["class_t", "class"]),
    ("CCITypeID", ["type_id_t", "type_id"]),
    ("CCIMultiLevelTypeID", ["ml_type_id"]),
    ("CCIFunctionalID", ["functional_id"]),
    ("CCIMultiLevelLocationID", ["ml_location_id"]),
    ("CCISingleLevelID", ["single_id"]),
    ("CCISingleLevelLocationAtID", ["location_at_id"]),
    ("CCIClassification", ["classification_t", "classification"]),
]


def pset_file(header_note=""):
    lines = [
        "#",
        "# PropertySet definition for Construction Classification "
        "International",
    ]
    if header_note:
        lines.append("# " + header_note)
    lines += [
        "#",
        "# Format:",
        "#    PropertySet:   <Pset Name>   I[nstance]/T[ype]   "
        "<element list separated by ','>",
        "#       <Property Name 1>   <Data type>   "
        "<[opt] Revit parameter name, if different from IFC>",
        "#",
        "",
        "PropertySet:\t%s\tI\tIfcRoot" % PSET_NAME,
    ]
    for ifc_name, keys in _ORDER:
        for key in keys:
            lines.append("\t%s\tText\t%s" % (ifc_name, formats.PARAM[key]))
    return "\r\n".join(lines) + "\r\n"


def classification_settings(ifc):
    """Rows for Revit's IFC export > Classification Settings dialog."""
    return [
        ("Name", ifc["name"]),
        ("Source (Publisher)", ifc["source"]),
        ("Edition", ifc["edition"]),
        ("Edition date", ifc["edition_date"]),
        ("Documentation location", ifc["location"]),
        ("Classification field name", ifc["field"]),
    ]
