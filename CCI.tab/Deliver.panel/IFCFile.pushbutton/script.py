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
low = path.lower()
if "downloads" in low or "\\temp" in low or "desktop" in low:
    out.print_md("> " + t("ifc.keep_file"))
out.print_md("### " + t("ifc.steps"))
out.print_md("1. " + t("ifc.s1"))
out.print_md("2. " + t("ifc.s2"))
out.print_md("3. " + t("ifc.s3", path=path))
out.print_table([[k, v] for k, v in
                 ifcmap.classification_settings(settings["ifc"])],
                columns=[t("ifc.col_field"), t("ifc.col_value")])
out.print_md("4. " + t("ifc.s4"))
out.print_md("5. " + t("ifc.s5"))
out.print_md("### " + t("ifc.check"))
for key in ("ifc.check1", "ifc.check2", "ifc.check3"):
    out.print_md("- " + t(key))
script.show_file_in_explorer(path)
