# CCI-EN (pyRevit extension)

CCI classification for Revit following BIM Ísland's guidelines:
*CCI leiðbeiningar* (edition 2, 11.01.2023), *CCI leiðbeiningar fyrir Revit*
(edition 1, 30.01.2023) and *Þróunarstig byggingarhluta* (REV4). The same
tool exists in Icelandic as **CCI-IS**; install one of them, not both.

## Install
Put the `CCI-EN.extension` folder in `%APPDATA%\pyRevit\Extensions\` and
click Reload in pyRevit. A **CCI** tab appears. Revit 2024 or later,
pyRevit's IronPython engine.

## Order of work
1. **Project setup**: tick the scope (BIM Ísland, p. 1), set the building
   number, storey codes (01, K1, M2) and LOD per element group. Saved in the
   project, so everyone on a central model shares it.
2. **CCI table**: shows which CCI table is in use and loads newer ones
   (see below). Ships with Molio's tables of 2020-05-26 (R1).
3. **Parameters**: adds the 11 parameters (plus `CCIClassification`)
   under Identity Data, `[Type]` ones as type parameters, the rest as
   instance parameters, only on the categories they belong to. Choose
   Molio's file or the tool's own file (see *Shared parameter file*).
4. **Classify**: one row per type (and per room name) with a suggested
   class. Edit, untick what should wait, then *Write to model*. Writes
   `CCIClassCode[Type]`, `CCITopnode[Type]` and `CCIClassification[Type]`.
   With elements selected, only their types are shown. *Pick from table*
   searches the whole CCI table. The *Source* column says where a
   suggestion comes from (Guidelines = BIM Ísland's/Molio's guides,
   Suggestion = the tool, Studio = a studio rule). Tick *Remember* and the
   class is saved as a studio rule for that family and type (or room name).
5. **Number**: `%QQC001`, `§B.AD.QQC001` and `#QQC001`, per the scope.
6. **Locations**: `B01.01.001` on rooms, `+B01.01.001` on elements in rooms.
7. **Check**: report with links to the elements, CSV if wanted.
8. **IFC file**: writes `CCI_in_Revit_to_IFC.txt` and shows the
   Classification Settings values.

## What stays put
- **Numbers never change.** A type or element keeps its number. Deleted
  numbers are not reused. If a type changes class it gets a new number in the
  new class, and the old one is retired. Numbers already in the model (typed
  by hand) are adopted when they are free.
- **Instance values win over type values** (BIM Ísland). The tool copies type
  values onto instances (can be turned off in setup) but never overwrites an
  instance value someone changed on purpose.

## Required by scope and LOD

| Scope | Fills / checks |
|---|---|
| Coordinated information exchange | CCIClassCode, CCITypeID |
| System diagrams and controls | CCIClassCode, CCIFunctionalID (checks format only) |
| Operations | CCITopnode, CCIClassCode, CCIMultiLevelTypeID, CCIMultiLevelLocationID |
| Product ID | CCISingleLevelID |
| Location ID | CCISingleLevelLocationAtID |

Classification and type ID are only required from **LOD 300** (openings
from LOD 325, and a unique ID at LOD 400), per *Þróunarstig byggingarhluta*.

## The CCI table, and keeping it up to date
The tool ships with Molio's CCI tables of **2020-05-26, R1** (construction
elements, use of spaces, use of construction entities, construction aids:
722 + 148 + 174 + 74 classes). Molio IKT's current free downloads
(P150a–d) are this same edition, so it is up to date as of November 2026.
The **CCI table** button:

- **Update from link**: paste a web address or a path on a shared drive,
  several separated by a space. Accepts Molio's spreadsheets (.xlsx,
  Danish and/or English) or a table in the tool's own format (.json). The
  link is remembered, so the next update is one click.
- **Update from files**: the same, from files you pick.
- Before anything changes, you see what is new, removed and renamed, and
  **which codes used in the open model are not in the new table**. Older
  versions are kept; **Switch version** goes back.
- **Studio data folder**: by default `%APPDATA%\CCI-tools`. Point it at a
  shared drive and the whole studio uses the same table, rules and
  Icelandic names. Updating the extension never touches it.

The project remembers which table it was classified with, and Check says
if the active table is a different one.

To make a .json table outside Revit: `python tools/build_table.py <xlsx…>`.

## Models with old coding
Many models already have CCI (or CCS) coding from an earlier tool or
template. The *Now* column in Classify shows it.

- **Replace old coding** puts the tool's suggestion in place of codes that
  differ from it or are not in the CCI table. It works on the selected rows,
  or on every row with old coding when nothing is selected. Nothing is
  written until *Write to model*. Rows with old coding but no suggestion
  are left for you to pick from the table.
- **Also overwrite codes set on single elements**: normally the tool
  leaves an instance value alone, because BIM Ísland lets instance values
  override the type on purpose. Tick this to clear old codes on elements
  as well.
- **Number** rewrites type IDs and product IDs to the current class, so
  old IDs are replaced too. Hand-made subtypes (`%QQC01.001`) are kept.
- The tool only touches types that are placed in the model. Unused types
  keep whatever they had.
- Where the template has `CCIClassName[Type]` and
  `CCIClassCodeVersion[Type]`, as Molio's file does, Classify fills those
  as well: the English class name and the table edition (R1).

## CCIClassification and IFC
Revit's IFC exporter reads the classification field as
`[System]Code:Description`. The tool writes `AD:Wall construction`: the
code, then Molio's English name. The system name comes from IFC
Classification Settings ("CCI Classification"), and the topnode has its own
parameter, as BIM Ísland's IDS expects. Earlier versions of this tool wrote
`[L]AD`, which Revit would export as a classification system called "L".
Check flags that format, and running Classify again fixes it. Values like
`[CCI][L]AD:Wall construction` from other tools are accepted.

The property set file maps the CCI parameters as `Text`, as in BIM
Ísland's guide. They are codes, not numbers, so text is correct.

## Check
Besides errors, Check prints a **classification overview**: each category
and the codes it got, with names and counts. That is where you spot a
wrong class. The check itself verifies format and that a code exists in
the table, not that it is the right code for the element. Elements set not
to export to IFC are skipped. Elements outside the LOD groups (generic
models etc.) only give warnings.

## Shared parameter file
Molio's official CCI shared parameter file and its IFC property set file
are tool package **C420 + C421**, part of Molio's paid *CAD og
bygningsmodel* subscription. A free Molio IKT account gives the CCI tables
(P150) but not these files.

Until the studio has C420, **Parameters > The tool's own file** adds the
same parameter names from a file the tool writes itself. What that means:

- **IFC deliveries are the same.** IFC export maps the parameters by
  name (`CCI_in_Revit_to_IFC.txt`, written by the IFC button from BIM
  Ísland's guide), and BIM Ísland's IDS checks read the IFC. Neither sees
  GUIDs.
- **GUIDs differ from Molio's.** Revit tells shared parameters apart by
  GUID, so a model made with Molio's file and one made with the tool's
  file don't share schedules or tags across links, and copy/paste
  between them can create a second `CCIClassCode`. The tool's GUIDs are
  the same in every copy of the tool, so partners can use the same file:
  **Parameters > Save the tool's file**.
- **Switching later is safe.** When you get C420, run **Parameters >
  Molio's file**. The tool offers to move the project over: it reads
  every value, swaps the parameters and writes the values back, all in
  one undoable step. Check says which file a project uses. Families that
  have the CCI parameters built in need updating separately.
- **If a model already has the CCI parameters** (e.g. from the studio's
  template), **Parameters > Save the file from this project** writes a
  shared parameter file with that project's GUIDs. Use it for other
  projects, and every project matches the template.
- If Molio's file spells a name differently in upper/lower case (BIM
  Ísland's IDS report writes `CCITopNode`, the Revit guide
  `CCITopnode`), the tool uses whatever spelling the project has.

## Icelandic names
419 of the 1,044 classes have Icelandic names (plus 67 group names): all
functional and technical
systems, all space uses, the component groups, the components architects
use most, and construction entity groups. Terms BIM Ísland uses are
marked `bim_island`; **the rest are drafts and need a review** by someone
who knows Icelandic building terminology. Classes without a name are shown
in English in brackets.

Review workflow: **CCI table > Export Icelandic names (CSV)**, edit the
`is` column in Excel, set `status` to `reviewed`, then **Import
Icelandic names**. Names are saved in the data folder. When a newer table
changes an English term, the Icelandic name is marked `stale` in the
export so it can be checked.

## Rules
Which class a Revit type gets comes from rules: the studio's own (data
folder, tried first) and the defaults (`data/rules.json`, generated by
`tools/make_rules.py`). A rule can look at category, family/type name,
room name, type parameters, structural and curtain. Rules with `match`
are tried before plain category rules. The defaults cover the main
architectural categories, MEP basics, and room names in Icelandic,
English and Danish (Stofa → AAB, Stigagangur → EAD, Sorpgeymsla → CAA…).

## Where the documents disagree, and what the tool does
- Type ID `%AD001` (CCI leiðbeiningar v2) vs `%AD1` (Þróunarstig, properties
  table): the tool follows v2, and the number of digits is a setting.
- Pset name `CCI_Administrative` (Revit guide) vs `CCS_Administrative`
  (Þróunarstig): the tool uses `CCI_Administrative`.
- `CCIClassification` is not among the 11 parameters, but the IFC export's
  "Classification field name" points at it. The tool fills it (`[L]AD`) when
  the parameter exists. **Test** in Revit's IFC export that `[L]` is not read
  as the classification's name; if it is, turn off "with domain first" in
  setup.
- **Smoke damper**: BIM Ísland's examples use `QMB` for *reykloka*, but
  in Molio's table `QMB` is "On-off spjæld / Gas shutoff valve" and the
  smoke damper is `FMB` (Røgspjæld). The tool maps *reykloka* to `FMB`
  and shut-off dampers to `QMB`. Worth confirming with BIM Ísland.
- Molio's CCS guide for architects (2020) uses some older CCS codes (e.g.
  `XLD` toilet); the tool uses the CCI table's codes (`XKB`).
- Molio's own spreadsheets disagree in a few places (e.g. space `AAA` is
  "Room" in the English file, "Courtyard" in the Danish file's English
  column; component `RLC` appears twice). The import takes each language
  from its own file and lists every disagreement.
- The Estonian/international CCI-EE template is a different edition of CCI
  (CCIC, not Molio) and is not used.
- Example `B2.K2.010` (summary table) vs `Bxx` (detailed section): the tool
  uses two digits, `B02.K2.010`.
- `§U.VV.XXXbbb`: "bbb" is described as a number per element, but the
  examples show a type number. Default: type number; can be switched in setup.

## Not yet
- A test of the parameter move against Molio's actual C420 file.
- A review of the Icelandic names.
- Automatic `CCIFunctionalID` (system numbering is the MEP engineers' job;
  the tool checks its format).
- Elements in linked models are not touched.

Guidelines: BIM Ísland (bim.is). CCI classes: Molio. Check the licence
terms of Molio's tables before the translated table is shared outside the
studio.
