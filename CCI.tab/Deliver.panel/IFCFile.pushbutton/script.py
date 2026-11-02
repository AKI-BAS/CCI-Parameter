# -*- coding: utf-8 -*-
"""IFC: write CCI_in_Revit_to_IFC.txt and show the Classification
Settings values for Revit's IFC export (CCI leiðbeiningar fyrir Revit,
bls. 3-4)."""
from __future__ import unicode_literals

import codecs

from pyrevit import forms, script

from cci import ifcmap
from cci.i18n import t
from cci.revit import ui

doc = ui.doc()
ui.require_project(doc)
settings = ui.settings_or_warn(doc)

path = forms.save_file(file_ext="txt", default_name="CCI_in_Revit_to_IFC",
                       title=t("ifc.pick"))
if not path:
    script.exit()
with codecs.open(path, "w", "utf-8") as f:
    f.write(ifcmap.pset_file())

out = ui.output()
out.print_md("## " + t("ifc.title"))
out.print_md(t("ifc.written", path=path))
out.print_md("### " + t("ifc.step1"))
out.print_md(t("ifc.step1_d"))
out.print_table([[k, v] for k, v in
                 ifcmap.classification_settings(settings["ifc"])],
                columns=[t("ifc.col_field"), t("ifc.col_value")])
out.print_md("### " + t("ifc.step2"))
out.print_md(t("ifc.step2_d", path=path))
out.print_md("### " + t("ifc.step3"))
out.print_md(t("ifc.step3_d"))
script.show_file_in_explorer(path)
