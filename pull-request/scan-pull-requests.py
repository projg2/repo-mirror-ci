#!/usr/bin/env python
# Scan open pull requests, update their statuses and print the next
# one for processing (if any).

from __future__ import print_function

import errno
import os
import pickle
import sys

import github


def main():
    GITHUB_USERNAME = os.environ['GITHUB_USERNAME']
    GITHUB_TOKEN_FILE = os.environ['GITHUB_TOKEN_FILE']
    GITHUB_REPO = os.environ['GITHUB_REPO']
    PULL_REQUEST_DB = os.environ['PULL_REQUEST_DB']

    with open(GITHUB_TOKEN_FILE) as f:
        token = f.read().strip()

    db = {}
    try:
        with open(PULL_REQUEST_DB, 'rb') as f:
            db = pickle.load(f)
    except (IOError, OSError) as e:
        if e.errno != errno.ENOENT:
            raise

    g = github.Github(GITHUB_USERNAME, token, per_page=250)
    r = g.get_repo(GITHUB_REPO)

    to_process = []

    for pr in r.get_pulls():
        # skip PRs marked noci
        if any(x.name == 'noci' for x in pr.labels):
            print('{}: noci'.format(pr.number),
                  file=sys.stderr)

            # if it made it to the cache, we probably need to wipe
            # pending status
            if pr.number in db:
                commit = pr.get_commits().reversed[0]
                for status in commit.get_statuses():
                    # skip foreign statuses
                    if status.creator.login != GITHUB_USERNAME:
                        continue
                    # if it's pending, mark it done
                    if status.state == 'pending':
                        commit.create_status(
                                context='gentoo-ci',
                                state='success',
                                description='Checks skipped due to [noci] label')
                    break
                del db[pr.number]

            continue

        # if it's not cached, get its status
        if pr.number not in db:
            print('{}: updating status ...'.format(pr.number), file=sys.stderr)
            commit = pr.get_commits().reversed[0]
            for status in commit.get_statuses():
                # skip foreign statuses
                if status.creator.login != GITHUB_USERNAME:
                    continue
                # if it's not pending, mark it done
                if status.state != 'pending':
                    db[pr.number] = commit.sha
                    print('{}: at {}'.format(pr.number, commit.sha),
                          file=sys.stderr)
                else:
                    db[pr.number] = ''
                    print('{}: found pending'.format(pr.number),
                          file=sys.stderr)
                break
            else:
                db[pr.number] = ''
                print('{}: unprocessed'.format(pr.number),
                      file=sys.stderr)

        if db.get(pr.number, '') != pr.head.sha:
            to_process.append(pr)

    to_process = sorted(to_process, key=lambda x: x.updated_at)
    for i, pr in enumerate(to_process):
        commit = pr.get_commits().reversed[0]
        if i == 0:
            desc = 'QA checks in progress...'
            db[pr.number] = commit.sha
        else:
            desc = 'QA checks pending. Currently {}. in queue.'.format(i)
        commit.create_status(
                context='gentoo-ci',
                state='pending',
                description=desc)

        print('{}: {} -> {}'.format(pr.number,
                db.get(pr.number, '') or '(none)', pr.head.sha),
              file=sys.stderr)

    with open(PULL_REQUEST_DB + '.tmp', 'wb') as f:
        pickle.dump(db, f)
    os.rename(PULL_REQUEST_DB + '.tmp', PULL_REQUEST_DB)

    if to_process:
        print(to_process[0].number)

    return 0


if __name__ == '__main__':
    sys.exit(main())
