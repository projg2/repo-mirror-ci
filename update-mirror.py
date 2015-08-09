#!/usr/bin/env python

import json
import os
import os.path
import sys
import xml.etree.ElementTree as et

import github


GITHUB_USERNAME = 'gentoo-repo-qa-bot'
GITHUB_TOKEN_FILE = os.path.expanduser('~/.github-token')
GITHUB_ORG = 'gentoo-mirror'


def gh_sources(r):
    return (
        ('git', r.clone_url),
        ('git', r.ssh_url),
        ('git', r.git_url),
        ('svn', r.svn_url + '/trunk'),
    )


# DTD expects a particular order
DTD_ORDER = ['name', 'description', 'longdescription', 'homepage',
        'owner', 'source', 'feed']


def dtd_sort_key(av):
    a, v = av
    if a in DTD_ORDER:
        return DTD_ORDER.index(a)
    else:
        return len(DTD_ORDER)


def main(summary_path, repos_xml_path):
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
    to_remove = []
    to_update = []
    for i, r in enumerate(gu.get_repos()):
        sys.stderr.write('\r@ scanning [%-3d/%-3d]' % (i+1, gu.public_repos))
        if r.name not in repos or repos[r.name]['x-should-remove']:
            to_remove.append(r)
        else:
            gh_repos.add(r.name)
            if repos[r.name]['x-can-update']:
                to_update.append(r)
            repos[r.name]['x-mirror-sources'] = gh_sources(r)
    sys.stderr.write('\n')

    # 1. delete stale repos
    for r in to_remove:
        sys.stderr.write('* removing %s\n' % r.name)
        r.delete()

    # 2. now create new repos :)
    for r, data in sorted(repos.items()):
        if r not in gh_repos and data['x-can-create']:
            sys.stderr.write('* adding %s\n' % r)
            # description[1+] can be other languages
            # sadly, layman gives us no clue what language it is...
            gr = gu.create_repo(r,
                    description = data.get('description', {}).get('en') or github.GithubObject.NotSet,
                    homepage = data.get('homepage') or github.GithubObject.NotSet,
                    has_issues = False,
                    has_wiki = False)
            repos[r]['x-mirror-sources'] = gh_sources(gr)
            to_update.append(gr)

    # 3. write a new repositories.xml for them
    root = et.Element('repositories')
    root.set('version', '1.0')

    for r, data in sorted(repos.items()):
        if 'x-mirror-sources' not in data:
            continue

        rel = et.Element('repo')
        for attr, val in sorted(data.items(), key=dtd_sort_key):
            if attr.startswith('x-'):
                continue
            elif attr == 'source': # replace
                for t, url in data['x-mirror-sources']:
                    subel = et.Element('source')
                    subel.set('type', t)
                    subel.text = url
                    rel.append(subel)
            elif attr in ('quality', 'status'): # attributes
                rel.set(attr, val)
            elif attr in ('name', 'homepage'): # single-value
                subel = et.Element(attr)
                subel.text = val
                rel.append(subel)
            elif attr in ('description', 'longdescription'): # lang-dict
                for l, v in val.items():
                    subel = et.Element(attr)
                    subel.set('lang', l)
                    subel.text = v
                    rel.append(subel)
            elif attr in ('owner', 'feed'): # lists
                for v in val:
                    subel = et.Element(attr)
                    if attr == 'owner':
                        for k, subval in v.items():
                            if k == 'type':
                                subel.set(k, subval)
                            else:
                                subsubel = et.Element(k)
                                subsubel.text = subval
                                subel.append(subsubel)
                    else:
                        subel.text = v
                    rel.append(subel)

        root.append(rel)

    xml = et.ElementTree(root)
    with open(repos_xml_path, 'wb') as f:
        f.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write(b'<!DOCTYPE repositories SYSTEM "http://www.gentoo.org/dtd/repositories.dtd">\n')
        xml.write(f, 'UTF-8', False)

    print('DELETED_REPOS = %s' % ' '.join(r.name for r in to_remove))
    print('REPOS = %s' % ' '.join(r.name for r in to_update))


if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:]))
