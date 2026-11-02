# -*- coding: utf-8 -*-
"""Stable running numbers.

A number, once given, stays with that element/type for the life of the
project: re-running never renumbers, and numbers of deleted items are not
handed out again (no two things ever share a number over time, so old
drawings, schedules and IFCs stay unambiguous).

The registry is plain JSON-able data and is stored in the Revit project.

    {"counters": {"type:QQC": 4, "single:QQC": 120},
     "items":    {"type:QQC": {"<uniqueId>": 1, ...}, ...}}
"""
from __future__ import unicode_literals

from cci import formats


class Registry(object):

    def __init__(self, data=None):
        data = data or {}
        self.counters = dict(data.get("counters", {}))
        self.items = dict((k, dict(v)) for k, v in data.get("items", {}).items())
        # type UniqueId -> {"u": "B", "vv": "AD"}: the functional and
        # technical system chosen in Classify, used for §U.VV.XXX.
        self.parents = dict(data.get("parents", {}))

    def to_data(self):
        return {"counters": dict(self.counters),
                "items": dict((k, dict(v)) for k, v in self.items.items()),
                "parents": dict(self.parents)}

    def get(self, series, uid):
        return self.items.get(series, {}).get(uid)

    def allocate(self, series, uid):
        """Number for uid in series; existing numbers are kept."""
        bucket = self.items.setdefault(series, {})
        if uid in bucket:
            return bucket[uid]
        n = self.counters.get(series, 0) + 1
        bucket[uid] = n
        self.counters[series] = n
        return n

    def adopt(self, series, uid, number):
        """Take over a number that is already in the model.

        Returns False if another item already holds it (duplicate), so the
        caller can give uid a new number instead.
        """
        bucket = self.items.setdefault(series, {})
        for other, n in bucket.items():
            if n == number and other != uid:
                return False
        bucket[uid] = number
        if number > self.counters.get(series, 0):
            self.counters[series] = number
        return True

    def move(self, old_series, new_series, uid):
        """Item changed class: it gets a number in the new series.

        The old number is retired, not reused.
        """
        bucket = self.items.get(old_series, {})
        if uid in bucket:
            del bucket[uid]
        return self.allocate(new_series, uid)

    def find(self, kind, uid):
        """Series of this kind ('type', 'single', ...) holding uid."""
        prefix = kind + ":"
        for s, bucket in self.items.items():
            if s.startswith(prefix) and uid in bucket:
                return s
        return None

    def number_for(self, series_key, uid, existing_value=None):
        """The number uid should have in series_key.

        - keeps a number it already has in this series;
        - if it was numbered under another class, that number is retired
          and it gets a new one in this series;
        - otherwise an ID already in the model (e.g. typed by hand or from
          an earlier tool) is adopted when it is free;
        - otherwise the next number.
        """
        if uid in self.items.get(series_key, {}):
            return self.items[series_key][uid]
        kind = series_key.split(":", 1)[0]
        old = self.find(kind, uid)
        if old:
            return self.move(old, series_key, uid)
        if existing_value:
            n = formats.number_of_id(existing_value)
            cls = formats.class_of_id(existing_value)
            if n and cls == series_key.split(":", 1)[1] and \
                    self.adopt(series_key, uid, n):
                return n
        return self.allocate(series_key, uid)

    def forget_missing(self, series, alive_uids):
        """Drop items that no longer exist. Counters are not lowered."""
        bucket = self.items.get(series, {})
        alive = set(alive_uids)
        for uid in list(bucket):
            if uid not in alive:
                del bucket[uid]


def series(kind, class_code):
    """Key for a numbering series, e.g. series('type', 'QQC') -> 'type:QQC'."""
    return "%s:%s" % (kind, class_code)


def resolve_instance(inst_value, old_type_value, new_type_value, copy):
    """What to write into an instance parameter when its type changes.

    BIM Ísland: instance values always win over type values. So an instance
    value is only replaced when it is empty or still equal to what the type
    had (i.e. it was a copy, not a deliberate override).

    copy: also write the type value onto instances (so IFC/schedules that
    read the instance parameter see it).
    Returns the value to write, or None to leave the instance alone.
    """
    inst_value = inst_value or ""
    is_override = inst_value and inst_value != (old_type_value or "") \
        and inst_value != (new_type_value or "")
    if is_override:
        return None
    if not copy:
        # Instance should be empty so it inherits from the type; clear only
        # stale copies.
        return "" if inst_value else None
    if inst_value == (new_type_value or ""):
        return None
    return new_type_value or ""
