# -*- coding: utf-8 -*-
"""Where tables, studio rules and Icelandic names live, so the tool can
grow without touching the extension:

    <extension>/data/             shipped with the tool (read-only)
        default.json              {"active_table": "<id>"}
        tables/<id>.json          the CCI table shipped
        rules.json                default mapping rules
        names_is.json             Icelandic names (drafts)

    <data folder>/                per user, or a shared studio folder
        cci-data.json             active table, link, history
        tables/<id>.json          tables loaded from a link or files
        rules.json                studio rules (tried before default ones)
        names_is.json             Icelandic names added or reviewed

The data folder defaults to %APPDATA%\\CCI-tools and can be pointed at a
network folder so the whole studio shares one table, one set of rules and
one set of names. Updating the extension never overwrites it.
"""
from __future__ import unicode_literals

import datetime
import os

from cci import compat, importer, rules, table


def _read(path, default):
    if not path or not os.path.exists(path):
        return default
    return compat.load_json(path)


class Store(object):

    def __init__(self, bundled_dir, user_dir):
        self.bundled = bundled_dir
        self.user = user_dir

    # --------------------------------------------------------- config
    def _config_path(self):
        return os.path.join(self.user, "cci-data.json")

    def config(self):
        cfg = {"active_table": None, "table_link": "", "history": []}
        cfg.update(_read(os.path.join(self.bundled, "default.json"), {}))
        user = _read(self._config_path(), {})
        cfg.update(user)
        return cfg

    def save_config(self, **changes):
        self._ensure()
        cfg = _read(self._config_path(), {})
        cfg.update(changes)
        compat.save_json(self._config_path(), cfg)

    def _ensure(self):
        for d in (self.user, os.path.join(self.user, "tables")):
            if not os.path.isdir(d):
                os.makedirs(d)

    # --------------------------------------------------------- tables
    def table_ids(self):
        """{id: path}; tables in the data folder win over shipped ones."""
        out = {}
        for base in (os.path.join(self.bundled, "tables"),
                     os.path.join(self.user, "tables")):
            if not os.path.isdir(base):
                continue
            for name in sorted(os.listdir(base)):
                if name.lower().endswith(".json"):
                    out[name[:-5]] = os.path.join(base, name)
        return out

    def active_id(self):
        ids = self.table_ids()
        want = self.config().get("active_table")
        if want in ids:
            return want
        return sorted(ids)[-1] if ids else None

    def load_table_data(self, table_id=None):
        table_id = table_id or self.active_id()
        path = self.table_ids().get(table_id)
        if not path:
            return None
        return importer.check_table(compat.load_json(path))

    def load_table(self, table_id=None):
        return table.ClassTable(self.load_table_data(table_id),
                                self.names())

    def save_table(self, data, source):
        """Store a new table and make it active. Returns its id."""
        importer.check_table(data)
        self._ensure()
        data = dict(data)
        data["imported"] = datetime.date.today().isoformat()
        data["imported_from"] = source
        path = os.path.join(self.user, "tables", data["id"] + ".json")
        compat.save_json(path, data)
        cfg = self.config()
        history = [h for h in cfg.get("history", [])
                   if h.get("id") != data["id"]]
        history.append({"id": data["id"], "name": data.get("name", ""),
                        "imported": data["imported"], "source": source})
        self.save_config(active_table=data["id"], history=history)
        return data["id"]

    def set_active(self, table_id):
        if table_id not in self.table_ids():
            raise KeyError(table_id)
        self.save_config(active_table=table_id)

    # ---------------------------------------------------------- names
    def names(self):
        out = dict(_read(os.path.join(self.bundled, "names_is.json"),
                         {}).get("names", {}))
        out.update(_read(os.path.join(self.user, "names_is.json"),
                         {}).get("names", {}))
        return out

    def save_names(self, updates):
        self._ensure()
        path = os.path.join(self.user, "names_is.json")
        data = _read(path, {"names": {}})
        data.setdefault("names", {}).update(updates)
        compat.save_json(path, data)
        return len(updates)

    # ---------------------------------------------------------- rules
    def rules_layers(self):
        return [_read(os.path.join(self.user, "rules.json"), {"rules": []}),
                _read(os.path.join(self.bundled, "rules.json"),
                      {"rules": []})]

    def ruleset(self, default_topnodes=None):
        return rules.RuleSet.from_layers(self.rules_layers(),
                                         default_topnodes)

    def add_rule(self, rule):
        """Add or replace (same id) a studio rule."""
        self._ensure()
        path = os.path.join(self.user, "rules.json")
        data = _read(path, {"rules": []})
        data["rules"] = [r for r in data.get("rules", [])
                         if r.get("id") != rule["id"]]
        data["rules"].insert(0, rule)
        compat.save_json(path, data)
