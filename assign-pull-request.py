#!/usr/bin/env python

import json
import os
import os.path
import sys

import github
import lxml.etree


def map_dev(dev, dev_mapping):
    if dev.lower() in dev_mapping:
        return '@' + dev_mapping[dev]
    if dev.endswith('@gentoo.org'):
        dev = dev[:-len('@gentoo.org')]
    else:
        dev = dev.replace('@', '[at]')
    return '~~%s~~' % dev


def map_proj(proj, proj_mapping):
    if proj.lower() in proj_mapping:
        return '@' + proj_mapping[proj]
    if proj.endswith('@gentoo.org'):
        proj = proj[:-len('@gentoo.org')]
    else:
        proj = proj.replace('@', '[at]')
    return '~~[%s (project)]~~' % proj


def main(prid, ref_repo_path):
    GITHUB_DEV_MAPPING = os.environ['GITHUB_DEV_MAPPING']
    GITHUB_PROJ_MAPPING = os.environ['GITHUB_PROJ_MAPPING']
    GITHUB_USERNAME = os.environ['GITHUB_USERNAME']
    GITHUB_TOKEN_FILE = os.environ['GITHUB_TOKEN_FILE']
    GITHUB_REPO = os.environ['GITHUB_REPO']

    with open(GITHUB_TOKEN_FILE) as f:
        token = f.read().strip()

    g = github.Github(GITHUB_USERNAME, token, per_page=50)
    r = g.get_repo(GITHUB_REPO)
    # issue API fits us better here
    pr = r.get_issue(int(prid))

    # check if assigned already
    if pr.assignee:
        return 0
    for l in pr.get_labels():
        if l.name in ('assigned', 'need assignment'):
            return 0

    # delete old results
    old_comment_found = False
    for co in pr.get_comments():
        if co.user.login == GITHUB_USERNAME:
            if 'Pull Request assignment' not in co.body:
                continue
            old_comment_found = True
            co.delete()

    with open(GITHUB_DEV_MAPPING) as f:
        dev_mapping = json.load(f)
    with open(GITHUB_PROJ_MAPPING) as f:
        proj_mapping = json.load(f)
    with open(os.path.join(ref_repo_path, 'profiles/categories')) as f:
        categories = [l.strip() for l in f.read().splitlines()]

    areas = set()
    packages = set()
    for l in sys.stdin:
        path = l.strip().split('/')
        if path[0] in categories:
            areas.add('ebuilds')
            packages.add('/'.join(path[0:2]))
        elif path[0] == 'eclass':
            areas.add('eclasses')
        elif path[0] == 'profiles':
            if path[1] != 'use.local.desc':
                areas.add('profiles')
        elif path[0] == 'metadata':
            if path[1] not in ('md5-cache', 'pkg_desc_index'):
                areas.add('other files')
        else:
            areas.add('other files')

    body = '''Pull Request assignment

*Areas affected*: %s
*Packages affected*: %s%s
''' % (', '.join(sorted(areas)),
        ', '.join(sorted(packages)[0:5]),
        '...' if len(packages) > 5 else '')

    if packages:
        # now try to determine unique sets of maintainers
        # if we get too many unique sets, i.e. we would end up highlighting
        # everyone, do not auto-assign
        pkg_maints = {}
        unique_maints = set()
        new_package = False
        maint_needed = False
        cant_assign = False
        for p in packages:
            ppath = os.path.join(ref_repo_path, p, 'metadata.xml')
            try:
                metadata_xml = lxml.etree.parse(ppath)
            except OSError:
                # no metadata.xml? most likely a new package!
                pkg_maints[p] = ['@gentoo/proxy-maint (new package)']
                new_package = True
            else:
                all_ms = []
                for m in metadata_xml.getroot():
                    if m.tag != 'maintainer':
                        continue
                    if m.get('type') == 'project':
                        ms = map_proj(m.findtext('email'), proj_mapping)
                    else:
                        ms = map_dev(m.findtext('email'), dev_mapping)

                    for subm in m:
                        if m.tag == 'description' and m.get('lang', 'en') == 'en':
                            ms += ' (%s)' % m.text
                    all_ms.append(ms)

                if all_ms:
                    # not a single GitHubber? not good.
                    if not [x for x in all_ms if '@' in x]:
                        cant_assign = True
                    pkg_maints[p] = all_ms
                    unique_maints.add(tuple(sorted(all_ms)))
                    if len(unique_maints) > 5:
                        break
                else:
                    # maintainer-needed!
                    pkg_maints[p] = ['@gentoo/proxy-maint (maintainer needed)']
                    maint_needed = True

        if len(unique_maints) > 5:
            cant_assign = True
            body += '\n@gentoo/proxy-maint: Too many disjoint maintainers, disabling auto-assignment.'
        else:
            for p in sorted(packages):
                body += '\n**%s**: %s' % (p, ', '.join(pkg_maints[p]))
            if cant_assign:
                body += '\n\nAt least one of the listed packages is maintained entirely by non-GitHub developers!'
    else:
        cant_assign = True
        body += '\n@gentoo/proxy-maint'

    if maint_needed:
        pr.add_to_labels('maintainer-needed')
    if new_package:
        pr.add_to_labels('new ebuild')
    if cant_assign:
        pr.add_to_labels('need assignment')
    else:
        pr.add_to_labels('assigned')
    pr.create_comment(body)
    return 0


if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:]))
