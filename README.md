# CCI tools for Revit (source)

One source, two pyRevit extensions: **CCI-IS** (Icelandic) and **CCI-EN**
(English). User documentation: `docs/README-is.md`, `docs/README-en.md`.

```
src/lib/cci/          pure-Python core (IronPython 2.7 + CPython 3)
  formats.py          build/validate every CCI code (BIM Ísland v2)
  levels.py           storey codes, room numbers
  numbering.py        stable running numbers
  rules.py            Revit type -> CCI class rules (layered)
  importer.py         Molio xlsx / json tables -> table format, diff, CSV
  xlsx.py             xlsx reader that runs in IronPython
  table.py            class table + Icelandic names
  store.py            data folder: tables, versions, studio rules, names
  groups.py           LOD groups (Þróunarstig REV4), scope -> fields
  checker.py          model check
  settings.py         per-project settings
  ifcmap.py           CCI_in_Revit_to_IFC.txt
  i18n.py             text lookup (lang.json written by the build)
src/lib/cci/revit/    Revit API layer (storage, parameters, UI helpers)
src/buttons/<name>/   script.py (+ ui.xaml) per button
src/lang/is.json      all Icelandic text
src/lang/en.json      all English text
src/data/             tables/<id>.json, rules.json, names_is.json,
                      default.json
tools/                build_table.py (xlsx -> json), make_rules.py,
                      make_names.py + names_is.tsv
tests/                core tests, language/XAML checks, end-to-end
                      runs of the buttons on a fake Revit model
build.py              -> dist/CCI-IS.extension, dist/CCI-EN.extension
```

```
python -m pytest tests     # 300+ tests
python build.py            # needs Pillow
```

Text never goes in code: add a key to both `is.json` and `en.json`
(the tests fail if a key is missing from either, or their `{placeholders}`
differ).

## Install in pyRevit

There are two versions of the extension. Install **one** of them:

| Version   | Language  | Branch   |
|-----------|-----------|----------|
| CCI-IS    | Icelandic | `cci-is` |
| CCI-EN    | English   | `cci-en` |

### Option 1: Download (simplest, no git needed)

1. On this page, open the branch menu (top left, says `main`) and pick
   `cci-is`.
2. Click **Code → Download ZIP**.
3. Unzip it and rename the folder to `CCI-IS.extension` (the name must
   end in `.extension`).
4. Open File Explorer, paste `%APPDATA%\pyRevit\Extensions` into the
   address bar, and move the folder there.
5. In Revit: **pyRevit tab → Reload**. A **CCI** tab appears.

To update: download again and replace the folder.

### Option 2: pyRevit command line (easy updates)

Open PowerShell and run (one command, two lines):

```powershell
pyrevit extend ui CCI-IS https://github.com/AKI-BAS/CCI-Parameter.git `
  --branch=cci-is --username=AKI-BAS --password=YOUR-TOKEN
```

- `CCI-IS` is the name the extension gets in pyRevit.
- `--branch=cci-is` picks the Icelandic version. Use `cci-en` for English.
- The repository is private, so pyRevit needs your GitHub username and a
  token (GitHub → Settings → Developer settings → Personal access tokens,
  read-only access to this repository).
- It installs into pyRevit's own Extensions folder. Then **pyRevit tab →
  Reload**.

To update later:

```powershell
pyrevit extensions update CCI-IS
```

If a `CCI-IS.extension` folder is already in `%APPDATA%\pyRevit\Extensions`
(e.g. copied there by hand), delete it first, or pyRevit will show the
tab twice.

### For developers: making a new version

Edit `src/`, then run `python -m pytest tests` and `python build.py`.
Copy `dist/CCI-IS.extension/*` to the `cci-is` branch and
`dist/CCI-EN.extension/*` to the `cci-en` branch, and commit.

Keep this repository private: it includes Molio's CCI tables.
