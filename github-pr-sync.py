#!/usr/bin/env python

import datetime
import json
import os
import os.path
import sys
import tempfile

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
    def __init__(self, url_prefix, token):
        self.bz = bugz.bugzilla.BugzillaProxy(url_prefix + 'xmlrpc.cgi')
        self.token = token
        self.cache = {}

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

    def prefetch_bugs(self, bugs):
        params = {
            'Bugzilla_token': self.token,
            'ids': bugs,
        }
        print('Prefetching bugs %s...' % bugs)
        ret = self.bz.Bug.get(params)
        assert(len(ret['bugs']) == len(bugs))
        for b in ret['bugs']:
            self.cache[b['id']] = b

    def get_bug(self, bug_id):
        if bug_id in self.cache:
            return self.cache[bug_id]

        params = {
            'Bugzilla_token': self.token,
            'ids': [bug_id],
        }
        print('Fetching bug #%d...' % bug_id)
        ret = self.bz.Bug.get(params)
        assert(len(ret['bugs']) == 1)
        return ret['bugs'][0]

    def get_comments(self, bug_id):
        # TODO: use new_since to limit the list
        params = {
            'Bugzilla_token': self.token,
            'ids': [bug_id],
        }
        ret = self.bz.Bug.comments(params)
        assert(len(ret['bugs']) == 1)
        assert(len(ret['comments']) == 0)
        return ret['bugs'][str(bug_id)]['comments']

    def add_comment(self, bug_id, comment):
        params = {
            'Bugzilla_token': self.token,
            'id': bug_id,
            'comment': comment,
        }
        ret = self.bz.Bug.add_comment(params)
        return ret['id']

    def update_bug(self, bug_id, **data):
        params = {
            'Bugzilla_token': self.token,
            'ids': [bug_id],
        }
        params.update(data)
        ret = self.bz.Bug.update(params)
        assert(len(ret['bugs']) == 1)


def main(json_db):
    GITHUB_USERNAME = os.environ['GITHUB_USERNAME']
    GITHUB_TOKEN_FILE = os.environ['GITHUB_TOKEN_FILE']
    GITHUB_REPO = os.environ['GITHUB_REPO']

    BUGZILLA_URL = os.environ['BUGZILLA_URL']
    assert BUGZILLA_URL.endswith('/')
    BUGZILLA_TOKEN_FILE = os.environ['BUGZILLA_TOKEN_FILE']

    with open(GITHUB_TOKEN_FILE) as f:
        token = f.read().strip()
    with open(BUGZILLA_TOKEN_FILE) as f:
        bugz_token = f.read().strip()

    with open(json_db) as f:
        db = json.load(f)

    g = github.Github(GITHUB_USERNAME, token, per_page=50)
    r = g.get_repo(GITHUB_REPO)
    bz = BugzillaWrapper(BUGZILLA_URL, bugz_token)

    bz.prefetch_bugs([pr['bug-id'] for pr in db.values()])

    try:
        print('Fetching pull requests...')
        for pr in r.get_pulls(state = 'all'):
            if str(pr.number) not in db:
                db[str(pr.number)] = {}
            db_pr = db[str(pr.number)]

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
                # get initial comment id
                db_pr['bugzilla-comments'] = [
                        c['id'] for c in bz.get_comments(db_pr['bug-id'])
                        if c['count'] == 0]
                db_pr['github-comments'] = []
                print('PR #%d: filed bug #%d' % (pr.number, db_pr['bug-id']))

            bug = bz.get_bug(db_pr['bug-id'])

            # check if any changes occured
            pr_changed = True
            bug_changed = True

            if 'pr-updated-at' in db_pr:
                pr_uat = datetime.datetime.strptime(db_pr['pr-updated-at'], DATE_FORMAT)
                if pr.updated_at <= pr_uat:
                    print('PR #%d: PR not changed' % pr.number)
                    pr_changed = False
            if pr_changed:
                db_pr['pr-updated-at'] = pr.updated_at.strftime(DATE_FORMAT)

            bug_lastchange = datetime.datetime(*bug['last_change_time'].timetuple()[:6])
            if 'bug-updated-at' in db_pr:
                bug_uat = datetime.datetime.strptime(db_pr['bug-updated-at'], DATE_FORMAT)
                if bug_lastchange <= bug_uat: # TODO
                    print('PR #%d: bug not changed' % pr.number)
                    bug_changed = False
            if bug_changed:
                db_pr['bug-updated-at'] = bug_lastchange.strftime(DATE_FORMAT)

            if not pr_changed and not bug_changed:
                continue

            # sync new comments
            def get_github_comments():
                for f, t in ((pr.get_issue_comments, 'issue'),
                        (pr.get_review_comments, 'review')):
                    print('PR #%d: Fetching %s comments...' % (pr.number, t))
                    for c in f():
                        if c.id not in db_pr['github-comments']:
                            yield (c.created_at, t, c)

            def get_bugzilla_comments():
                print('PR #%d: Fetching bug comments...' % pr.number)
                for c in bz.get_comments(db_pr['bug-id']):
                    if c['id'] not in db_pr['bugzilla-comments']:
                        dt = datetime.datetime(*(c['creation_time'].timetuple()[:6]))
                        yield (dt, c)

            print('PR #%d: Syncing...' % pr.number)

            if pr_changed:
                for d, t, c in sorted(get_github_comments()):
                    # add to bugzilla
                    creator = c.user.login
                    if c.user.name:
                        creator += ' (%s)' % c.user.name

                    c_body = c.body
                    if t == 'review':
                        d_body = '\n'.join('> ' + l for l in c.diff_hunk.splitlines())
                        c_body = d_body + '\n' + c_body

                    body = '''(GitHub %(type)s comment by %(creator)s @ %(time)s)
    <%(url)s>

    %(body)s''' % {
                        'type': t,
                        'creator': creator,
                        'time': d.strftime(DATE_FORMAT),
                        'url': c.html_url,
                        'body': c_body,
                    }
                    db_pr['bugzilla-comments'].append(bz.add_comment(db_pr['bug-id'], body))
                    db_pr['github-comments'].append(c.id)
                    print('PR #%d: github comment %s/%s copied to bugzilla' % (pr.number, c.user.login, d.strftime(DATE_FORMAT)))

            if bug_changed:
                for d, c in sorted(get_bugzilla_comments()):
                    # add to github
                    url = '%sshow_bug.cgi?id=%d#c%d' % (BUGZILLA_URL,
                            c['bug_id'], c['id'])
                    body = '''[(Bugzilla comment #%(pos)d by %(creator)s @ %(time)s)](%(url)s)

    %(body)s''' % {
                        'pos': c['count'],
                        'creator': c['creator'],
                        'time': d.strftime(DATE_FORMAT),
                        'url': url,
                        'body': c['text'],
                    }
                    gc = pr.create_issue_comment(body)
                    db_pr['bugzilla-comments'].append(c['id'])
                    db_pr['github-comments'].append(gc.id)
                    print('PR #%d: bz comment #%d copied to github' % (pr.number, c['count']))

            # sync state
            # has bug been closed/reopened?
            if (bug['status'] != 'RESOLVED') != db_pr['is-open']:
                db_pr['is-open'] = (bug['status'] != 'RESOLVED')
                # propagate to pull request
                if (pr.state == 'open') != db_pr['is-open']:
                    if db_pr['is-open']:
                        comment = 'Reopening since the Gentoo bug has been reopened'
                        new_state = 'open'
                    else:
                        comment = ('Closing since the Gentoo has been resolved (%s)'
                                % bug['resolution'])
                        new_state = 'closed'
                    c = pr.create_issue_comment(comment)
                    db_pr['github-comments'].append(c.id)
                    pr.edit(state = new_state)
                    print('PR #%d: state -> %s due to bug resolution change (%s/%s)'
                            % (pr.number, new_state, bug['status'], bug['resolution']))
            # has PR been closed/reopened?
            elif (pr.state == 'open') != db_pr['is-open']:
                db_pr['is-open'] = (pr.state == 'open')
                # propagate to bug
                if (bug['status'] != 'RESOLVED') != db_pr['is-open']:
                    if db_pr['is-open']:
                        comment = 'Reopening since the pull request has been reopened'
                        new_status = 'CONFIRMED'
                        new_resolution = ''
                    else:
                        new_status = 'RESOLVED'
                        if pr.is_merged():
                            comment = 'Closing since the pull request has been merged'
                            new_resolution = 'FIXED'
                        else:
                            # we don't know why it was closed so let's just obso it
                            comment = 'Closing since the pull request has been closed'
                            new_resolution = 'OBSOLETE'
                    db_pr['bugzilla-comments'].append(
                            bz.add_comment(db_pr['bug-id'], comment))
                    bz.update_bug(db_pr['bug-id'],
                            status=new_status, resolution=new_resolution)
                    print('PR #%d: bug -> %s/%s due to pull request state change'
                            % (pr.number, new_status, new_resolution))
    finally:
        f = tempfile.NamedTemporaryFile('w',
                dir=os.path.dirname(json_db), delete=False)
        try:
            json.dump(db, f)
            f.close()
        except:
            os.unlink(f.name)
        else:
            os.rename(f.name, json_db)


if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:]))
