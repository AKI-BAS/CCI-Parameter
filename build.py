# -*- coding: utf-8 -*-
"""Build both pyRevit extensions from the one source:

    dist/CCI-IS.extension   (all text in Icelandic)
    dist/CCI-EN.extension   (all text in English)

Run:  python build.py          (needs Pillow for the icons)
"""
from __future__ import print_function, unicode_literals

import io
import json
import os
import shutil

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "src")
DIST = os.path.join(ROOT, "dist")

# panel key (folder name comes from lang "panel.<key>"), buttons
# button: (source folder, pushbutton folder name, icon text, colour)
PANELS = [
    ("setup", [
        ("setup", "ProjectSetup", "\u2699", "#2F5D62"),
        ("params", "Parameters", "{ }", "#2F5D62"),
        ("table", "Table", "CCI", "#2F5D62"),
    ]),
    ("classify", [
        ("classify", "Classify", "QQC", "#1F6F8B"),
        ("number", "Number", "%01", "#1F6F8B"),
        ("locations", "Locations", "+B", "#1F6F8B"),
    ]),
    ("deliver", [
        ("check", "Check", "\u2713", "#7A4E2D"),
        ("ifc", "IFCFile", "IFC", "#7A4E2D"),
    ]),
]
LANGS = {"is": "CCI-IS", "en": "CCI-EN"}
TAB = "CCI"


def q(text):
    """YAML double-quoted scalar (JSON strings are valid YAML)."""
    return json.dumps(text, ensure_ascii=False)


def write(path, text):
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def font(size):
    for name in ("DejaVuSans-Bold.ttf", "DejaVuSans.ttf", "arialbd.ttf"):
        for base in ("/usr/share/fonts/truetype/dejavu", "C:/Windows/Fonts",
                     ""):
            try:
                return ImageFont.truetype(os.path.join(base, name), size)
            except (IOError, OSError):
                continue
    return ImageFont.load_default()


def icon(path, text, colour, size=96):
    scale = 4
    big = size * scale
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([4 * scale, 4 * scale, big - 4 * scale,
                         big - 4 * scale], radius=18 * scale, fill=colour)
    fs = {1: 58, 2: 44, 3: 34}.get(len(text), 30) * scale
    f = font(fs)
    box = d.textbbox((0, 0), text, font=f)
    w, h = box[2] - box[0], box[3] - box[1]
    d.text(((big - w) / 2 - box[0], (big - h) / 2 - box[1]), text,
           font=f, fill="white")
    img.resize((size, size), Image.LANCZOS).save(path)


def build(lang):
    with io.open(os.path.join(SRC, "lang", lang + ".json"),
                 encoding="utf-8") as f:
        text = json.load(f)
    ext = os.path.join(DIST, LANGS[lang] + ".extension")
    if os.path.exists(ext):
        shutil.rmtree(ext)
    os.makedirs(ext)

    shutil.copytree(os.path.join(SRC, "lib"), os.path.join(ext, "lib"),
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    shutil.copy(os.path.join(SRC, "lang", lang + ".json"),
                os.path.join(ext, "lib", "cci", "lang.json"))
    shutil.copytree(os.path.join(SRC, "data"), os.path.join(ext, "data"))
    shutil.copy(os.path.join(ROOT, "docs", "README-%s.md" % lang),
                os.path.join(ext, "README.md"))

    tab = os.path.join(ext, TAB + ".tab")
    os.makedirs(tab)
    write(os.path.join(tab, "bundle.yaml"), "layout:\n" + "".join(
        "  - %s\n" % text["panel." + key] for key, _ in PANELS))
    for key, buttons in PANELS:
        panel = os.path.join(tab, text["panel." + key] + ".panel")
        os.makedirs(panel)
        write(os.path.join(panel, "bundle.yaml"), "layout:\n" + "".join(
            "  - %s\n" % b[1] for b in buttons))
        for src_name, folder, glyph, colour in buttons:
            btn = os.path.join(panel, folder + ".pushbutton")
            src = os.path.join(SRC, "buttons", src_name)
            shutil.copytree(src, btn, ignore=shutil.ignore_patterns(
                "__pycache__", "*.pyc"))
            write(os.path.join(btn, "bundle.yaml"),
                  "title: %s\ntooltip: %s\nauthor: %s\n" % (
                      q(text["btn.%s.title" % src_name]),
                      q(text["btn.%s.tip" % src_name]),
                      q("Sveinn Aki Olafs")))
            icon(os.path.join(btn, "icon.png"), glyph, colour)
    return ext


def main():
    for lang in LANGS:
        print("built", build(lang))


if __name__ == "__main__":
    main()
