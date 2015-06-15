#!/usr/bin/env python
# Sane wrapper to Portage syncing modules
# (one that actually returns an useful exit code)

from _emerge.actions import load_emerge_config
from _emerge.emergelog import emergelog
from _emerge.main import parse_opts

from portage.sync.controller import SyncManager

import os
import sys

def main(repo_name):
    actions, opts, _files = parse_opts([], silent=True)
    emerge_config = load_emerge_config(action='sync', args=_files, opts=opts)
    repo = emerge_config.target_config.settings.repositories[repo_name]
    os.umask(0o22)
    sync_manager = SyncManager(emerge_config.target_config.settings, emergelog)
    rc, message = sync_manager.sync(emerge_config, repo)
    return rc

if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:]))
