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
            borked.append(REPORT_URI_PREFIX + '/' + prhash + '/' + l)

    pre_borked = []
    fixed = []
    if borked:
        with open(pre_borked_path) as f:
            for l in f:
                lf = REPORT_URI_PREFIX + '/' + prhash + '/' + l
                if lf in borked:
                    pre_borked.append(lf)
                    borked.remove(lf)
                else:
                    fixed.append(lf)

    with open(GITHUB_TOKEN_FILE) as f:
        token = f.read().strip()

    g = github.Github(GITHUB_USERNAME, token, per_page=50)
    r = g.get_repo(GITHUB_REPO)
    pr = r.get_pull(int(prid))
    c = r.get_commit(commit_hash)

    report_url = REPORT_URI_PREFIX + '/' + prhash + '/output.html'
    if not borked and not pre_borked:
        c.create_status('success', description='All pkgcheck QA checks passed',
                target_url=report_url)
    else:
        body = ':disappointed: The QA check for this pull request has found the following issues:\n'
        if borked:
            body += '\nNew issues caused by PR:\n'
            for url in borked:
                body += url
        if pre_borked:
            body += '\nIssues inherited from Gentoo (may be modified by PR):\n'
            for url in pre_borked:
                body += url
        if fixed:
            body += '\nGentoo issues fixed by PR:\n'
            for url in fixed:
                body += url

        pr.create_issue_comment(body)
        c.create_status('failure', description='Some of the QA checks failed',
                target_url=report_url)


if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:]))
