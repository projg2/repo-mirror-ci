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



def main(commit_hash, desc):
    with open(GITHUB_TOKEN_FILE) as f:
        token = f.read().strip()

    g = github.Github(GITHUB_USERNAME, token, per_page=50)
    r = g.get_repo(GITHUB_REPO)
    c = r.get_commit(commit_hash)

    c.create_status('pending', description=desc)


if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:]))
