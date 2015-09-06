#!/usr/bin/python
import bugz.bugzilla
import json
import os
import os.path
import readline
import sys
import textwrap

REFERENCE_LOG_URL = 'https://qa-reports.gentoo.org/output/repos'

def main(bug_db_path):
    if not os.path.exists(bug_db_path):
        print('Refusing to proceed with non-existing bug-db.')
        print('Please initialize new bug-db with:')
        print("  echo {} > %s" % repr(bug_db_path))
        return 1

    with open(bug_db_path, 'r+') as f:
        bug_db = json.load(f)
    token_file = os.path.expanduser('~/.bugz_token')
    try:
        with open(token_file, 'r') as f:
            token = f.read().strip()
    except IOError:
        print('! Bugz token not found, please run "bugz login" first')
        return 1

    bz = bugz.bugzilla.BugzillaProxy('https://bugs.gentoo.org/xmlrpc.cgi')

    for r, bugs in bug_db.items():
        params = {
            'Bugzilla_token': token,
            'ids': list(bugs.values()),
            'url': '%s/%s.html' % (REFERENCE_LOG_URL, r),
        }
        ret = bz.Bug.update(params)
        print('Updated bugs %s' % [b['id'] for b in ret['bugs']])

    return 0


if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:]))
