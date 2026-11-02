# -*- coding: utf-8 -*-
"""Mapping rules: which CCI class a Revit type gets.

Rules live in rules.json files: the studio's own (in the data folder,
tried first) and the defaults shipped with the tool. A rule:

    {"id": "door",
     "category": ["OST_Doors"],
     "match": {"name_contains": ["glerhurð", "glass"],   # family or type name
               "not_contains": ["dummy"],
               "family": "Hurð", "type": "900",          # exact names
               "params": {"Function": "Exterior"},        # type/instance values
               "structural": false,
               "curtain": false},
     "class": "QQC",        # null = no code chosen yet
     "u": "B", "vv": "AD",  # functional / technical system for §U.VV.XXX
     "topnode": "L",
     "verified": true,      # code shown in BIM Ísland's or Molio's guides
     "note": "..."}

Order tried: rules with "match" (studio, then default), then plain
category rules (studio, then default); within a file, file order wins.
For rooms, "type" is the room name.
"""
from __future__ import unicode_literals

from cci import formats


def _lower(s):
    return (s or "").lower()


def _matches(rule, facts):
    cats = rule.get("category") or []
    if cats and facts.get("category") not in cats:
        return False
    m = rule.get("match") or {}
    name = _lower(facts.get("family")) + " " + _lower(facts.get("type"))
    words = m.get("name_contains")
    if words and not any(_lower(w) in name for w in words):
        return False
    for w in m.get("not_contains") or []:
        if _lower(w) in name:
            return False
    for key in ("family", "type"):
        # exact names, used by rules the studio saves from Classify
        if key in m and _lower(m[key]) != _lower(facts.get(key)):
            return False
    params = facts.get("params") or {}
    for key, want in (m.get("params") or {}).items():
        have = params.get(key)
        if isinstance(want, list):
            if have not in want:
                return False
        elif _lower("%s" % have) != _lower("%s" % want):
            return False
    for flag in ("structural", "curtain"):
        if flag in m and bool(facts.get(flag)) != bool(m[flag]):
            return False
    return True


class Result(object):
    def __init__(self, class_code=None, u=None, vv=None, topnode=None,
                 source="none", rule_id=None, verified=False,
                 studio=False):
        self.class_code = class_code
        self.u = u
        self.vv = vv
        self.topnode = topnode
        self.source = source
        self.rule_id = rule_id
        self.verified = verified
        self.studio = studio

    def __repr__(self):
        return "Result(%s, %s, %s)" % (self.class_code, self.source,
                                       self.rule_id)


class RuleSet(object):

    def __init__(self, data, default_topnodes=None):
        self._setup([data], default_topnodes)

    @classmethod
    def from_layers(cls, layers, default_topnodes=None):
        """layers: rule files, first one wins (studio before default).
        Order tried: specific rules of each layer, then plain category
        rules of each layer."""
        rs = cls.__new__(cls)
        rs._setup(layers, default_topnodes)
        return rs

    def _setup(self, layers, default_topnodes):
        self.specific, self.general = [], []
        self.n_layers = len(layers)
        all_rules = []
        for i, data in enumerate(layers):
            rules = [dict(r, _layer=i) for r in (data or {}).get("rules", [])]
            self.specific += [r for r in rules if r.get("match")]
            self.general += [r for r in rules if not r.get("match")]
            all_rules.append(rules)
        self.default_topnodes = default_topnodes or {
            "element": "L", "system": "L", "space": "B"}
        self.problems = []
        for rules in all_rules:
            self.problems += self._check(rules)

    @staticmethod
    def _check(rules):
        problems = []
        seen = set()
        for r in rules:
            rid = r.get("id")
            if not rid:
                problems.append(("rules.no_id", {}))
            elif rid in seen:
                problems.append(("rules.duplicate_id", {"id": rid}))
            seen.add(rid)
            code = r.get("class")
            if code and formats.check_class(code):
                problems.append(("rules.bad_class", {"id": rid,
                                                     "code": code}))
            tn = r.get("topnode")
            if tn and tn not in formats.TOPNODES:
                problems.append(("rules.bad_topnode", {"id": rid,
                                                       "code": tn}))
        return problems

    def classify(self, facts, kind="element"):
        for rules, source in ((self.specific, "rule"),
                              (self.general, "category")):
            for r in rules:
                if _matches(r, facts):
                    code = r.get("class")
                    return Result(
                        class_code=code or None,
                        u=r.get("u"), vv=r.get("vv"),
                        topnode=r.get("topnode")
                        or self.default_topnodes.get(kind, "L"),
                        source=source if code else "pending",
                        rule_id=r.get("id"),
                        verified=bool(r.get("verified")) and bool(code),
                        studio=self.n_layers > 1 and r["_layer"] == 0)
        return Result(topnode=self.default_topnodes.get(kind, "L"))
