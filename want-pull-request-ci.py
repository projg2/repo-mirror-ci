#!/usr/bin/env python

import os
import sys

import github


def main(prid):
    GITHUB_USERNAME = os.environ['GITHUB_USERNAME']
    GITHUB_TOKEN_FILE = os.environ['GITHUB_TOKEN_FILE']
    GITHUB_REPO = os.environ['GITHUB_REPO']

    with open(GITHUB_TOKEN_FILE) as f:
        token = f.read().strip()

    g = github.Github(GITHUB_USERNAME, token, per_page=50)
    r = g.get_repo(GITHUB_REPO)
    pr = r.get_issue(int(prid))

    if pr.state != 'open':
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:]))
