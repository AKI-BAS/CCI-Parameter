# -*- coding: utf-8 -*-
"""Fetch table files from web addresses or shared-drive paths."""
from __future__ import unicode_literals

import os
import shutil
import tempfile

from cci import importer


def fetch(links):
    """Copy/download each link into a temp folder.

    Returns (paths, problems) where problems are (i18n key, params).
    """
    folder = tempfile.mkdtemp(prefix="cci-table-")
    paths, problems = [], []
    for i, link in enumerate(links):
        target = os.path.join(folder, "file%d" % i)
        try:
            if link.lower().startswith(("http://", "https://")):
                _download(link, target)
            else:
                shutil.copy(link, target)
        except Exception as ex:  # network, missing file, access
            problems.append(("table.fetch_failed",
                             {"link": link, "error": "%s" % ex}))
            continue
        with open(target, "rb") as f:
            head = f.read(8)
        ext = importer.guess_ext(link, head)
        if not ext:
            problems.append(("table.unknown_type", {"link": link}))
            continue
        name = os.path.basename(link.split("?")[0]) or "table"
        if not name.lower().endswith(ext):
            name += ext
        final = os.path.join(folder, "%02d-%s" % (i, name))
        os.rename(target, final)
        paths.append(final)
    return paths, problems


def _download(url, target):
    from System.Net import (SecurityProtocolType, ServicePointManager,
                            WebClient)
    try:
        ServicePointManager.SecurityProtocol = \
            ServicePointManager.SecurityProtocol | SecurityProtocolType.Tls12
    except Exception:
        pass
    client = WebClient()
    try:
        client.Headers.Add("User-Agent", "CCI-tools (pyRevit)")
        client.DownloadFile(url, target)
    finally:
        client.Dispose()
