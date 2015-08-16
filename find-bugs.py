#!/usr/bin/env python
#  vim:se fileencoding=utf8
# (c) 2015 Michał Górny

import bugz.bugzilla
import json
import os.path
import re
import sys


bug_summaries = {
    'Missing masters= specification': 'MISSING_MASTERS',
    'Repository URI unaccessible': 'SYNC_FAIL',
    'Conflicting repository name': 'CONFLICTING_REPO_NAME',
    'Ebuild failures occuring in global scope': 'BAD_CACHE',
}


def main(bug_db_path, summary_path):
    if not os.path.exists(bug_db_path):
        print('Refusing to proceed with non-existing bug-db.')
        print('Please initialize new bug-db with:')
        print("  echo {} > %s" % repr(bug_db_path))
        return 1

    with open(bug_db_path, 'r+') as f:
        bug_db = json.load(f)
    with open(summary_path) as f:
        summary = json.load(f)

    params = {}

    token_file = os.path.expanduser('~/.bugz_token')
    try:
        with open(token_file, 'r') as f:
            params['Bugzilla_token'] = f.read().strip()
    except IOError:
        print('! Bugz token not found, will try anonymous')

    bz = bugz.bugzilla.BugzillaProxy('https://bugs.gentoo.org/xmlrpc.cgi')

    # summary matcher
    sum_re = re.compile(r'^\[(.*?)\] (.*)$')

    # find all blockers of tracker bug
    params['ids'] = ['repository-qa-issues']
    ret = bz.Bug.get(params)
    assert(len(ret['bugs']) == 1)

    # and now get buginfo for each of them
    params['ids'] = ret['bugs'][0]['depends_on']
    ret = bz.Bug.get(params)
    for b in ret['bugs']:
        m = sum_re.match(b['summary'])
        if not m:
            print('Unknown bug summary: %s' % b['summary'])
            continue

        repo = m.group(1)
        # skip removed repos unless not resolved yet
        if repo not in summary and b['resolution']:
            continue

        try:
            issue = bug_summaries[m.group(2)]
        except KeyError:
            print('Unknown issue for %s: %s' % (repo, m.group(2)))
            continue

        print(bug_db.get(repo, {}))
        if issue in bug_db.get(repo, {}):
            assert(bug_db[repo][issue] == b['id'])
            continue

        if repo not in bug_db:
            bug_db[repo] = {}
        bug_db[repo][issue] = b['id']

    with open(bug_db_path + '.new', 'w') as f:
        json.dump(bug_db, f)
    os.rename(bug_db_path + '.new', bug_db_path)

    return 0


if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:]))
