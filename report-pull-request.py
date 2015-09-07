#!/usr/bin/env python

import json
import os
import os.path
import sys
import xml.etree.ElementTree as et

import github


GITHUB_USERNAME = 'gentoo-repo-qa-bot'
GITHUB_TOKEN_FILE = os.path.expanduser('~/.github-token')
GITHUB_REPO = 'gentoo/gentoo'

REPORT_URI_PREFIX = 'https://qa-reports.gentoo.org/output/gentoo-ci/'



def main(prid, prhash, borked_path):
    borked = []
    with open(borked_path) as f:
        for l in f:
            borked.append(REPORT_URI_PREFIX + prhash + '/' + l)

    with open(GITHUB_TOKEN_FILE) as f:
        token = f.read().strip()

    g = github.Github(GITHUB_USERNAME, token, per_page=50)
    r = g.get_repo(GITHUB_REPO)
    pr = r.get_pull(int(prid))

    if not borked:
        body = ':+1: The QA check for this pull requests confirms no issues.'
    else:
        body = ':-1: The QA check for this pull request has found the following issues:\n\n'
        for url in borked:
            body += url

        body += '\nPlease note that the issues may come from the underlying Gentoo repository state rather than the pull request itself.'

    pr.create_issue_comment(body)


if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:]))
