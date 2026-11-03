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

## Branches

| Branch   | What                                   |
|----------|----------------------------------------|
| `main`   | CCI-IS extension (Icelandic), ready to install |
| `en`     | CCI-EN extension (English), ready to install   |
| `source` | this source code, tests and build script       |

`main` is the default, so the plain repository link installs the
Icelandic extension:

```powershell
pyrevit extend ui CCI-IS https://github.com/AKI-BAS/CCI-Parameter.git `
  --username=AKI-BAS --password=TOKEN
```

English: add `--branch=en` and use the name `CCI-EN`. Install one, not
both. Full install guide: the README on `main` (Icelandic) or `en`.

### For developers: making a new version

Edit `src/`, then run `python -m pytest tests` and `python build.py`.
Copy `dist/CCI-IS.extension/*` to the `main` branch and
`dist/CCI-EN.extension/*` to the `en` branch, and commit.

Keep this repository private: it includes Molio's CCI tables.
