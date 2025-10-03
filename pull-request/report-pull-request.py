#!/usr/bin/env python

import datetime
import os
import os.path
import sys

import github


def main(prid, prhash, borked_path, pre_borked_path, commit_hash):
    GITHUB_USERNAME = os.environ['GITHUB_USERNAME']
    GITHUB_TOKEN_FILE = os.environ['GITHUB_TOKEN_FILE']
    GITHUB_REPO = os.environ['GITHUB_REPO']

    REPORT_URI_PREFIX = os.environ['GENTOO_CI_URI_PREFIX']

    borked = []
    with open(borked_path) as f:
        for l in f:
            borked.append(REPORT_URI_PREFIX + '/' + prhash + '/output.html#' + l)

    pre_borked = []
    too_many_borked = False
    if borked:
        with open(pre_borked_path) as f:
            for l in f:
                if l.strip() == 'ETOOMANY':
                    too_many_borked = True
                    break

                lf = REPORT_URI_PREFIX + '/' + prhash + '/output.html#' + l
                if lf in borked:
                    pre_borked.append(lf)
                    borked.remove(lf)

    with open(GITHUB_TOKEN_FILE) as f:
        token = f.read().strip()

    g = github.Github(GITHUB_USERNAME, token, per_page=50)
    r = g.get_repo(GITHUB_REPO)
    pr = r.get_pull(int(prid))
    c = r.get_commit(commit_hash)

    # delete old results
    had_broken = False
    old_comments = []
    # note: technically we could have multiple leftover comments
    for co in pr.get_issue_comments():
        if co.user.login == GITHUB_USERNAME:
            if 'All QA issues have been fixed' in co.body:
                had_broken = False
            elif 'has found no issues' in co.body:
                had_broken = False
            elif 'No issues found' in co.body:
                had_broken = False
            elif 'New issues' in co.body:
                had_broken = True
            elif 'Issues already there' in co.body:
                had_broken = True
            elif 'Issues inherited from Gentoo' in co.body:
                had_broken = True
            else:
                # skip comments that don't look like CI results
                continue
            old_comments.append(co)
    for co in old_comments:
        co.delete()

    report_url = REPORT_URI_PREFIX + '/' + prhash + '/output.html'
    body = '''## Pull request CI report

*Report generated at*: %s
*Newest commit scanned*: %s
*Status*: %s
''' % (datetime.datetime.now(datetime.UTC).strftime('%Y-%m-%d %H:%M UTC'),
       commit_hash,
       ':x: **broken**' if borked else ':white_check_mark: good')

    if borked or pre_borked:
        if borked:
            if too_many_borked:
                body += '\nThere are too many broken packages to determine whether the breakages were added by the pull request. If in doubt, please rebase.\n\nIssues:'
            else:
                body += '\nNew issues caused by PR:\n'
            for url in borked:
                body += url
        if pre_borked:
            body += '\nThere are existing issues already. Please look into the report to make sure none of them affect the packages in question:\n%s\n' % report_url
    elif had_broken:
        body += '\nAll QA issues have been fixed!\n'
    else:
        body += '\nNo issues found\n'

    pr.create_issue_comment(body)

    if borked:
        c.create_status('failure', description='PR introduced new issues',
                target_url=report_url, context='gentoo-ci')
    elif pre_borked:
        c.create_status('success', description='No new issues found',
                target_url=report_url, context='gentoo-ci')
    else:
        c.create_status('success', description='All pkgcheck QA checks passed',
                target_url=report_url, context='gentoo-ci')


if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:]))
