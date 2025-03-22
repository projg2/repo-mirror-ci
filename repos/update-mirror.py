#!/usr/bin/env python

import json
import os
import sys

import github


def gh_sources(r):
    return (
        ('git', r.clone_url),
        ('git', r.ssh_url),
        ('git', r.git_url),
        ('svn', r.svn_url + '/trunk'),
    )


def main(summary_path):
    GITHUB_USERNAME = os.environ['GITHUB_USERNAME']
    GITHUB_TOKEN_FILE = os.environ['GITHUB_TOKEN_FILE']
    GITHUB_ORG = os.environ['GITHUB_ORG']

    with open(summary_path) as f:
        repos = json.load(f)

    with open(GITHUB_TOKEN_FILE) as f:
        token = f.read().strip()

    g = github.Github(GITHUB_USERNAME, token, per_page=50)
    gu = g.get_organization(GITHUB_ORG)
    gh_repos = set()

    # check repo states
    for data in repos.values():
        # 1. we don't add repos with broken metadata but we also don't
        # remove existing ones -- we hope maintainers will fix them,
        # or overlays team will remove them
        #
        # 2. remove repos with unsupported VCS -- this means that
        # upstream has switched, and there's no point in keeping
        # an outdated mirror
        #
        # 3. we can't update repos which are broken to the point of
        # being implicitly removed

        data['x-can-create'] = data['x-state'] in ('GOOD', 'BAD_CACHE')
        data['x-can-update'] = data['x-can-create']
        data['x-should-remove'] = data['x-state'] in ('REMOVED', 'UNSUPPORTED')

    # 0. scan all repos
    to_archive = []
    to_update = []
    for i, r in enumerate(gu.get_repos()):
        sys.stderr.write('\r@ scanning [%-3d/%-3d]' % (i+1, gu.public_repos))
        if r.name not in repos or repos[r.name]['x-should-remove']:
            if not r.description.startswith("[ARCHIVED] "):
                to_archive.append(r)
        else:
            gh_repos.add(r.name)
            if repos[r.name]['x-can-update']:
                to_update.append(r)
            repos[r.name]['x-mirror-sources'] = gh_sources(r)
    sys.stderr.write('\n')

    # 1. archive stale repos
    for r in to_archive:
        sys.stderr.write('* archiving %s\n' % r.name)
        r.edit(description="[ARCHIVED] " + r.description)

    # 1a. update repo metadata
    for r, data in sorted(repos.items()):
        if r in to_update:
            meta_changes = {
                "description": ' '.join(data.get('description', {}).get('en', "").split()),
                "homepage": data.get('homepage', ""),
            }
            if meta_changes["description"] == r.description:
                del meta_changes["description"]
            if meta_changes["homepage"] == r.homepage:
                del meta_changes["homepage"]
            if meta_changes:
                r.edit(**meta_changes)

    # 2. now create new repos :)
    for r, data in sorted(repos.items()):
        if r not in gh_repos and data['x-can-create']:
            sys.stderr.write('* adding %s\n' % r)
            gr = gu.create_repo(r,
                    description = ' '.join(data.get('description', {}).get('en').split()) or github.GithubObject.NotSet,
                    homepage = data.get('homepage') or github.GithubObject.NotSet,
                    has_issues = False,
                    has_wiki = False)
            repos[r]['x-mirror-sources'] = gh_sources(gr)
            to_update.append(gr)

    print('DELETED_REPOS = %s' % ' '.join(r.name for r in to_archive))
    print('REPOS = %s' % ' '.join(r.name for r in to_update))


if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:]))
