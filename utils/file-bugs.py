#!/usr/bin/env python
#  vim:se fileencoding=utf8
# (c) 2017 Michał Górny

import bugzilla
import configparser
import json
import os
import os.path
import readline
import sys
import textwrap


REFERENCE_LOG_URL = 'https://qa-reports.gentoo.org/output/repos'


class BugDesc(object):
    def __init__(self, summary, msg):
        self.summary = summary
        self.msg = '\n\n'.join(textwrap.fill(x, 72)
                for x in msg.split('\n\n'))


class StateHandlers(object):
    def REMOVED(self, repo, data):
        pass

    def GOOD(self, repo, data):
        pass

    def BAD_CACHE(self, repo, data):
        summary = '[%s] Ebuild failures occuring in global scope' % repo
        msg = ('''
Our automated repository checks [1] have detected that the '%s'
repository contains ebuilds that trigger fatal errors during the cache
regeneration. This usually means that the ebuilds call 'die' in global
scope indicating serious issues or have other serious QA violations.

Global-scope failures prevent the ebuild not only from being installed
but also from being properly processed by the Package Manager. Since
metadata can not be obtained for those ebuilds, no cache entries are
created for them and the Package Manager needs to retry running them
every time it stumbles upon them. This involves both a serious slowdown
and repeating error output while performing dependency resolution.

The most common cause of global-scope failures is use of removed or
banned APIs in old ebuilds. In particular, this includes eclasses being
removed or removing support for old EAPIs. Nonetheless there are also
other issues such as performing illegal operations in global scope
(external program calls), malformed bash in ebuilds or malformed
metadata.xml.

The error log for the repository can be found at:

  %s/%s.html

In particular, please look for highlighted '!!! ERROR' and '!!! caught
exception' lines. The former usually mean failures coming from eclasses
and the ebuild itself, while exceptions usually mean malformed ebuilds
or metadata.xml.

Please note that due to technical limitations of pkgcore, the processing
stops on the first error found. Once solved, please wait ~30 minutes
for the report to refresh in case new errors may appear.

Please fix the issue ASAP, possibly via removing unmaintained, old
ebuilds. We reserve the right to remove the repository from our list if
we do not receive any reply within 4 weeks.

[1]:https://wiki.gentoo.org/wiki/Project:Repository_mirror_and_CI
''' % (repo, REFERENCE_LOG_URL, repo)).strip()

        return BugDesc(summary, msg)

    def SYNC_FAIL(self, repo, data):
        summary = '[%s] Repository URI unaccessible' % repo
        uris = '\n\n'.join(
                '  [%8s] %s' % (r['type'], r['uri'])
                for r in data['source'])
        msg = ('''
Our automated repository checks [1] have detected that the '%s'
repository can not be synced.

The following URIs are listed for the repository:

%s

Please verify that the server hosting the repository is working
correctly. If the repository has been moved to a new location or removed
altogether, please let us know to update the record appropriately.

We reserve the right to remove the repository if we do not receive any
reply within 2 weeks.

[1]:https://wiki.gentoo.org/wiki/Project:Repository_mirror_and_CI
''' % (repo, uris)).strip()

        return BugDesc(summary, msg)

    def MISSING_MASTERS(self, repo, data):
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

    def MISSING_REPO_NAME(self, repo, data):
        summary = '[%s] Missing profiles/repo_name' % repo
        msg = ('''
Our automated repository checks [1] have detected that the repository
registered as '%s' is missing a repository name in profiles/repo_name
file.

This is going to cause issues with various Package Managers and even may
render the repository unusable to our users.

Please create the profiles/repo_name file, and type the repository name
inside. It needs to be equal to the name on the list ('%s'). If you
would like to use another name, please let us know. However, please note
that our tools provide no meaningful way of informing users that
a repository has been renamed -- therefore it is no different from
removing and re-adding the repository with a new name.

Please fix the issue ASAP. It prevents our tools from working on the
repository, and mirroring it. We reserve the right to remove it if we
do not receive any reply within 2 weeks.

[1]:https://wiki.gentoo.org/wiki/Project:Repository_mirror_and_CI
''' % (repo, repo)).strip()

        return BugDesc(summary, msg)

    def CONFLICTING_REPO_NAME(self, repo, data):
        summary = '[%s] Conflicting repository name' % repo
        msg = ('''
Our automated repository checks [1] have detected that the repository
registered as '%s' is using a different repo_name in %s
file:

    %s

This is going to cause issues with various Package Managers and even may
render the repository unusable to our users.

Please either set the repository name in %s to '%s', or let us know that you
would like to have the repository renamed on the official repository
list. However, please note that our tools provide no meaningful way of
informing users that a repository has been renamed -- therefore it is no
different from removing and re-adding the repository with a new name.

Please fix the issue ASAP. It prevents our tools from working on the
repository, and mirroring it. We reserve the right to remove it if we
do not receive any reply within 2 weeks.

[1]:https://wiki.gentoo.org/wiki/Project:Repository_mirror_and_CI
''' % (repo, data['x-repo-where'], data['x-repo-name'], data['x-repo-where'], repo)).strip()

        return BugDesc(summary, msg)

    def INVALID_MASTERS(self, repo, data):
        summary = '[%s] Invalid masters declared' % repo
        msg = ('''
Our automated repository checks [1] have detected that the repository
registered as '%s' is using one or more master repositories that are
either invalid or unreachable. The invalid masters are:

    %s

This is going to cause issues with various Package Managers and even may
render the repository unusable to our users.

Please ensure that the master list contains correct repository names
and that all the masters are available in the official repository list.
If necessary, please either remove invalid masters (and stop relying
on them) or request adding them to the list.

Furthermore, please note that listing the repository itself as its
master is invalid and meaningless. Depending on the implementation,
it may trigger infinite loops or be ignored.

Please fix the issue ASAP. It prevents our tools from working on the
repository, and mirroring it. We reserve the right to remove it if we
do not receive any reply within 2 weeks.

[1]:https://wiki.gentoo.org/wiki/Project:Repository_mirror_and_CI
''' % (repo, ' '.join(data['x-wrong-masters']))).strip()

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
        print('Put bugzilla API key into ~/.bugz_token')
        return 1

    bz = bugzilla.Bugzilla('https://bugs.gentoo.org',
                           api_key=token)

    sth = StateHandlers()

    for r, v in bug_db.items():
        if r not in summary:
            summary[r] = {'x-state': 'REMOVED'}

    expected_open_bugs = {}
    for r, v in sorted(summary.items()):
        issue = v['x-state']
        current_bugs = bug_db.get(r, {})

        if issue in current_bugs:
            print('%s: %s already filed as #%d'
                    % (r, issue, bug_db[r][issue]))
            expected_open_bugs[bug_db[r][issue]] = (r, issue)
            continue

        w = getattr(sth, issue)(r, v)
        if w is not None:
            if issue in current_bugs:
                continue

            owners = [o['email'] for o in v['owner']]
            params = {
                'product': 'Gentoo Linux',
                'component': 'Overlays',
                'version': 'unspecified',
                'summary': w.summary,
                'description': w.msg,
                'url': '%s/%s.html' % (REFERENCE_LOG_URL, r),
                'assigned_to': owners[0],
                'cc': ', '.join(owners[1:]),
                'blocks': ['repository-qa-issues'],
            }
            createinfo = bz.build_createbug(**params)

            # print the bug and ask for confirmation
            print('Owners: %s' % owners)
            print('Summary: %s' % params['summary'])
            print('Full log: %s' % params['url'])
            print()
            print(params['description'])
            print()
            resp = input('File the bug? [Y/n]')
            if resp.lower() in ('', 'y', 'yes'):
                try:
                    ret = bz.createbug(createinfo)
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
                            createinfo = bz.build_createbug(**params)
                            ret = bz.createbug(createinfo)

                            break
                    else:
                        raise
                print('Bug filed as #%d' % ret.id)
                print()

                if r not in bug_db:
                    bug_db[r] = {}
                bug_db[r][issue] = ret.id

                with open(bug_db_path + '.new', 'w') as f:
                    json.dump(bug_db, f)
                os.rename(bug_db_path + '.new', bug_db_path)
        elif current_bugs: # update existing bugs
            bug_ids = list(current_bugs.values())
            ret = bz.getbugs(bug_ids)
            for i, b in reversed(list(enumerate(ret))):
                # skip bugs that were already resolved
                if b is None:
                    print('Warning: getting #%d failed' % bug_ids[i])
                    del bug_ids[i]
                elif b.resolution:
                    del bug_ids[i]

            if bug_ids:
                params = {}
                params['status'] = 'RESOLVED'
                if issue == 'REMOVED':
                    params['resolution'] = 'OBSOLETE'
                    params['comment'] = 'The repository has been removed, rendering this bug obsolete.'
                else:
                    params['resolution'] = 'FIXED'
                    params['comment'] = 'The bug seems to be fixed in the repository. Closing.'

                updateinfo = bz.build_update(**params)

                print('Bugs: %s' % bug_ids)
                print('Repository: %s' % r)
                print('Status: %s/%s' % (params['status'], params['resolution']))
                print()
                print(params['comment'])
                print()
                resp = input('Update the bugs? [Y/n]')
                if resp.lower() in ('', 'y', 'yes'):
                    ret = bz.update_bugs(bug_ids, updateinfo)
                    print('Updated bugs %s' % [b['id'] for b in ret['bugs']])

            del bug_db[r]

            with open(bug_db_path + '.new', 'w') as f:
                json.dump(bug_db, f)
            os.rename(bug_db_path + '.new', bug_db_path)

    bug_ids = list(expected_open_bugs)
    if bug_ids:
        ret = bz.getbugs(bug_ids)
        for b in ret:
            if b is None:
                print('Warning: getting some bugs failed')
                continue
            # warn about bugs that were resolved (incorrectly?)
            if b.resolution:
                print('Warning: #%d (%s) %s/%s'
                        % (b.id, ': '.join(expected_open_bugs[b.id]),
                            b.status, b.resolution))

    return 0


if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:]))
