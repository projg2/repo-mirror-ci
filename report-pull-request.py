#!/usr/bin/env python

import json
import os
import os.path
import sys
import xml.etree.ElementTree as et

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
            elif 'The QA check for this pull request has found the following issues' in co.body:
                had_broken = True
            else:
                # skip comments that don't look like CI results
                continue
            old_comments.append(co)
    for co in old_comments:
        co.delete()

    report_url = REPORT_URI_PREFIX + '/' + prhash + '/output.html'
    if borked or pre_borked:
        body = ':disappointed: The QA check for this pull request has found the following issues:\n'
        if borked:
            if not too_many_borked:
                body += '\nNew issues caused by PR:\n'
            for url in borked:
                body += url
        if pre_borked:
            body += '\nIssues already there before the PR (double-check them):\n'
            for url in pre_borked:
                body += url
        if too_many_borked:
            body += '\nThere are too many broken packages to determine whether the breakages were added by the pull request. If in doubt, please rebase.'
        pr.create_issue_comment(body)
    elif had_broken:
        body = ':+1: All QA issues have been fixed!\n'
        pr.create_issue_comment(body)
    else:
        body = 'CI scan has found no issues in this pull request\n'
        pr.create_issue_comment(body)

    if borked:
        c.create_status('failure', description='PR introduced new issues',
                target_url=report_url)
    elif pre_borked:
        c.create_status('success', description='No new issues found',
                target_url=report_url)
    else:
        c.create_status('success', description='All pkgcheck QA checks passed',
                target_url=report_url)


if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:]))
