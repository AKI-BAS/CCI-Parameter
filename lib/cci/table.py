# -*- coding: utf-8 -*-
"""The CCI class table in use, with Icelandic names laid over it."""
from __future__ import unicode_literals

from cci import importer

_DOMAIN_OF_TOPNODE = {"L": "L", "A": "S", "B": "S", "E": "E", "D": "D"}


def domain_for(topnode):
    """'[L]' / 'L' -> 'L', '[A]'/'[B]' -> 'S', '[E]' -> 'E', else None."""
    if not topnode:
        return None
    return _DOMAIN_OF_TOPNODE.get(topnode.strip("[]"))


class ClassTable(object):

    def __init__(self, data, names=None):
        data = data or importer.empty_table()
        self.data = data
        self.id = data.get("id", "")
        self.title = data.get("name", "") or self.id
        self.complete = bool(data.get("complete"))
        self.domains = data.get("domains", {})
        self.groups = data.get("groups", {})
        self.names = names or {}

    # ---------------------------------------------------------- lookup
    def entry(self, code, topnode=None):
        d = domain_for(topnode)
        if d:
            return self.domains.get(d, {}).get(code)
        for dom in importer.DOMAINS:
            e = self.domains.get(dom, {}).get(code)
            if e:
                return e
        return None

    def known(self, code, topnode=None):
        return self.entry(code, topnode) is not None

    def _key(self, code, topnode):
        d = domain_for(topnode)
        if d:
            return d + ":" + code
        for dom in importer.DOMAINS:
            if code in self.domains.get(dom, {}):
                return dom + ":" + code
        return None

    def name(self, code, lang, topnode=None):
        """Name in the UI language. Icelandic falls back to English, with
        the English in brackets so it is clear it is untranslated."""
        e = self.entry(code, topnode)
        if not e:
            return ""
        if lang == "is":
            key = self._key(code, topnode)
            n = self.names.get(key, {}) if key else {}
            if n.get("is"):
                return n["is"]
            return "(%s)" % (e.get("en") or e.get("da") or "")
        return e.get("en") or e.get("da") or ""

    def name_status(self, code, topnode=None):
        e = self.entry(code, topnode)
        key = self._key(code, topnode)
        if not e or not key:
            return None
        return importer.name_status(e, self.names.get(key, {}))

    def group_name(self, kind, code, lang):
        e = self.groups.get(kind, {}).get(code)
        if not e:
            return ""
        if lang == "is":
            n = self.names.get("group:%s:%s" % (kind, code), {})
            if n.get("is"):
                return n["is"]
        return e.get("en") or e.get("da") or ""

    def path(self, code, lang, topnode=None):
        """'Opening/closing object > Space access object > Door'."""
        d = domain_for(topnode) or "L"
        parts = []
        if d == "L" and len(code) == 3:
            for g in (code[0], code[:2]):
                n = self.group_name("component", g, lang)
                if n:
                    parts.append(n)
        elif d == "L" and len(code) == 2:
            n = self.group_name("technical", code[0], lang)
            if n:
                parts.append(n)
        elif d == "D" and len(code) == 2:
            n = self.group_name("aid", code[0], lang)
            if n:
                parts.append(n)
        elif d in ("S", "E"):
            for g in range(1, len(code)):
                n = self.name(code[:g], lang, "[A]" if d == "S" else "[E]")
                if n:
                    parts.append(n)
        parts.append(self.name(code, lang, topnode))
        return " > ".join(p for p in parts if p)

    # ---------------------------------------------------------- search
    def choices(self, domain, lang, kinds=None):
        """[(code, label)] for a picker, sorted by code.

        kinds: table kinds to include, e.g. ('technical', 'component').
        """
        out = []
        top = {"L": "[L]", "S": "[A]", "E": "[E]", "D": "[D]"}[domain]
        for code in sorted(self.domains.get(domain, {})):
            e = self.domains[domain][code]
            if kinds and e.get("table") not in kinds:
                continue
            label = self.name(code, lang, top)
            if lang == "is" and e.get("en") and not label.startswith("("):
                label = "%s (%s)" % (label, e["en"])
            out.append((code, label))
        return out

    def search(self, text, domain, lang, limit=50):
        text = (text or "").strip().lower()
        out = []
        for code, label in self.choices(domain, lang):
            e = self.domains[domain][code]
            hay = " ".join([code, label, e.get("en", ""), e.get("da", ""),
                            e.get("def_en", "")]).lower()
            if not text or text in hay:
                out.append((code, label))
                if len(out) >= limit:
                    break
        return out

    def coverage(self):
        """(translated, total) names for Icelandic."""
        total = done = 0
        for d in importer.DOMAINS:
            for code in self.domains.get(d, {}):
                total += 1
                if self.names.get(d + ":" + code, {}).get("is"):
                    done += 1
        return done, total
