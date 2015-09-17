#!/usr/bin/env python

import datetime
import json
import os
import os.path
import sys

import bugz.bugzilla
import github


DATE_FORMAT = '%Y-%m-%d %H:%M:%SZ'


def initial_pr_body(pr):
    return '''
== == == == == == == == == == == == == == == == == == == == == == == ==

This bug has been filed automatically for GitHub pull request #%(number)d:

  %(url)s

All comments and bug resolutions will be automatically copied from
and to GitHub, so please do not cross-post to both. In order to test
the changes locally, you can use the following commands in your local
Gentoo checkout:

  git remote add github https://github.com/gentoo/gentoo.git
  git config --add remote.github.fetch '+refs/pull/*/head:refs/pull/*'
  git fetch github
  git checkout pull/%(number)d

In order to merge the pull request afterwards:

  git checkout master
  git pull --ff-only
  git merge -S pull/%(number)d
  git push --signed

If you need to rebase the commits against updated master:

  git pull --rebase=preserve -S

== == == == == == == == == == == == == == == == == == == == == == == ==

%(body)s
'''.strip() % {'number': pr.number, 'url': pr.html_url, 'body': pr.body}


class BugzillaWrapper(object):
    def __init__(self, token):
        self.bz = bugz.bugzilla.BugzillaProxy('https://mgorny:oe9to(Doox]eek4z@bugstest.gentoo.org/xmlrpc.cgi')
        self.token = token

    def file_bug(self, **data):
        params = {
            'Bugzilla_token': self.token,
            # defaults
            'product': 'Gentoo Linux',
            'component': 'Applications',
            'version': 'unspecified',
            'assigned_to': 'bug-wranglers@gentoo.org',
        }
        params.update(data)
        ret = self.bz.Bug.create(params)
        return ret['id']

    def get_bug(self, bug_id):
        # TODO: cache bugs for all PRs
        params = {
            'Bugzilla_token': self.token,
            'ids': [bug_id],
        }
        ret = self.bz.Bug.get(params)
        assert(len(ret['bugs']) == 1)
        return ret['bugs'][0]

def main(json_db):
    GITHUB_USERNAME = os.environ['GITHUB_USERNAME']
    GITHUB_TOKEN_FILE = os.environ['GITHUB_TOKEN_FILE']
    GITHUB_REPO = os.environ['GITHUB_REPO']

    BUGZILLA_TOKEN_FILE = os.environ['BUGZILLA_TOKEN_FILE']

    with open(GITHUB_TOKEN_FILE) as f:
        token = f.read().strip()
    with open(BUGZILLA_TOKEN_FILE) as f:
        bugz_token = f.read().strip()

    with open(json_db) as f:
        db = json.load(f)

    g = github.Github(GITHUB_USERNAME, token, per_page=50)
    r = g.get_repo(GITHUB_REPO)
    bz = BugzillaWrapper(bugz_token)

    for pr in r.get_pulls(state = 'all'):
        if str(pr.number) in db:
            db_pr = db[str(pr.number)]
            uat = datetime.datetime.strptime(db_pr['updated_at'], DATE_FORMAT)
            # TODO: bug updated-at too
            if pr.updated_at <= uat:
                pass # continue
        else:
            db_pr = {}
            db[str(pr.number)] = db_pr

        db_pr['updated_at'] = pr.updated_at.strftime(DATE_FORMAT)

        # create a bug if necessary
        if not 'bug-id' in db_pr:
            # skip already-closed PRs
            if pr.state != 'open':
                continue
            db_pr['bug-id'] = bz.file_bug(
                summary = pr.title,
                description = initial_pr_body(pr),
                url = pr.html_url,
                blocks = ['pull-requests'],
                alias = 'github:%d' % pr.number,
            )
            db_pr['is-open'] = True
            db_pr['bugzilla-comments'] = []
            db_pr['github-comments'] = []
            print('PR %d: filed bug #%d' % (pr.number, db_pr['bug-id']))

        bug = bz.get_bug(db_pr['bug-id'])

        # sync state
        # has bug been closed/reopened?
        if (bug['status'] != 'RESOLVED') != db_pr['is-open']:
            db_pr['is-open'] = (bug['status'] != 'RESOLVED')
            # propagate to pull request
            if (pr.state == 'open') != db_pr['is-open']:
                if db_pr['is-open']:
                    comment = 'Reopening since the Gentoo bug has been reopened'
                else:
                    comment = ('Closing since the Gentoo has been resolved (%s)'
                            % bug['resolution'])
                c = pr.create_issue_comment(comment)
                db_pr['github-comments'].append(c.id)
                pr.edit(state = ('open' if db_pr['is-open'] else 'closed'))
                print('PR %d: %s due to bug resolution change (%s/%s)'
                        % (pr.number, 'reopened' if db_pr['is-open'] else 'closed',
                            bug['status'], bug['resolution']))
        # has PR been closed/reopened?
        elif (pr.state == 'open') != db_pr['is-open']:
            db_pr['is-open'] = (pr.state == 'open')
            # propagate to bug
            if (bug['status'] != 'RESOLVED') != db_pr['is-open']:
                if db_pr['is-open']:
                    # reopen bug
                    print('-> REOPEN BUG')
                else:
                    # close bug
                    print('-> CLOSE BUG')

        from IPython import embed
        embed()
        break

        break

    with open(json_db, 'w') as f:
        json.dump(db, f)


if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:]))
