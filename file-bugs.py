#!/usr/bin/env python
#  vim:se fileencoding=utf8
# (c) 2015 Michał Górny

import bugz.bugzilla
import json
import os
import os.path
import readline
import sys
import textwrap


class BugDesc(object):
    def __init__(self, summary, msg):
        self.summary = summary
        self.msg = '\n\n'.join(textwrap.fill(x, 72)
                for x in msg.split('\n\n'))


class StateHandlers(object):
    def GOOD(self, repo):
        pass

    def BAD_CACHE(self, repo):
        pass

    def SYNC_FAIL(self, repo):
        pass

    def MISSING_MASTERS(self, repo):
        summary = '[%s] Missing masters= specification' % repo
        msg = ('''
Our automated repository checks [1] have detected that the '%s'
repository lacks masters= specification. This causes some Package
Managers to be unable to use the repository, and will become fatal in
Portage at some point.

Master repositories provide various resources to the sub-repositories
in the way of inheritance. For example, a repository inherits eclasses,
licenses, mirrors provided by the master. Additionally, it requires
the master repository to be enabled, therefore allowing the packages
provided by it to satisfy dependencies.

In particular, if your repository uses any eclasses, licenses, mirrors,
global USE flags or any other resources provided by the Gentoo
repository, or depends on any packages provided by it, it needs to
specify in metadata/layout.conf:

    masters = gentoo

However, if your repository is fully stand-alone and any package
provided by it can be installed without any other repository being
enabled, you should specify empty masters= to indicate this:

    masters =

Please fix the issue ASAP. It prevents our tools from working on the
repository, and mirroring it. We reserve the right to remove it if we
do not receive any reply within 2 weeks.

[1]:https://wiki.gentoo.org/wiki/Project:Repository_mirror_and_CI
''' % repo).strip()

        return BugDesc(summary, msg)

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

    token_file = os.path.expanduser('~/.bugz_token')
    try:
        with open(token_file, 'r') as f:
            token = f.read().strip()
    except IOError:
        print('! Bugz token not found, please run "bugz login" first')
        return 1

    bz = bugz.bugzilla.BugzillaProxy('https://bugs.gentoo.org/xmlrpc.cgi')

    sth = StateHandlers()

    for r, v in sorted(summary.items()):
        issue = v['x-state']
        w = getattr(sth, issue)(r)
        if w is not None:
            if bug_db.get(r):
                if issue in bug_db[r]:
                    print('%s: %s already filed as #%d'
                            % (r, issue, bug_db[r][issue]))
                    continue
                else:
                    raise NotImplementedError('New issue with the same repository')

            # TODO: get all owners
            owners = (v['owner_email'],)

            params = {
                'Bugzilla_token': token,
                'product': 'Gentoo Infrastructure',
                'component': 'Gentoo Overlays',
                'version': 'unspecified',
                'summary': w.summary,
                'description': w.msg,
                'assigned_to': owners[0],
                'cc': ', '.join(owners[1:]),
                'blocks': ['repository-qa-issues'],
            }

            # print the bug and ask for confirmation
            print('Owners: %s' % owners)
            print('Summary: %s' % params['summary'])
            print()
            print(params['description'])
            print()
            resp = input('File the bug? [Y/n]')
            if resp.lower() in ('', 'y', 'yes'):
                try:
                    ret = bz.Bug.create(params)
                except Exception as e:
                    for o in owners:
                        if o in e.faultString:
                            print('Owner not on Bugzie, reassigning...')

                            params['description'] = ('''
== == == == == == == == == == == == == == == == == == == == == == == ==
The repository owner is not registered on Bugzilla
Owner: %s
== == == == == == == == == == == == == == == == == == == == == == == ==

''' % owners) + params['description']
                            params['assigned_to'] = 'overlays@gentoo.org'
                            params['cc'] = []
                            params['blocks'].append('repository-qa-bugzie')
                            ret = bz.Bug.create(params)

                            break
                    else:
                        raise
                print('Bug filed as #%d' % ret['id'])
                print()

                if r not in bug_db:
                    bug_db[r] = {}
                bug_db[r][issue] = ret['id']

                with open(bug_db_path + '.new', 'w') as f:
                    json.dump(bug_db, f)
                os.rename(bug_db_path + '.new', bug_db_path)

    return 0


if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:]))
