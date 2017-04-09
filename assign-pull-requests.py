#!/usr/bin/env python

import json
import os
import os.path
import socket
import sys

import github
import lxml.etree


def map_dev(dev, dev_mapping):
    if dev_mapping.get(dev.lower()):
        return '@' + dev_mapping[dev.lower()]
    if dev.endswith('@gentoo.org'):
        dev = dev[:-len('@gentoo.org')]
    else:
        dev = dev.replace('@', '[at]')
    return '~~%s~~' % dev


def map_proj(proj, proj_mapping):
    if proj.lower() in proj_mapping:
        return '@' + proj_mapping[proj.lower()]
    if proj.endswith('@gentoo.org'):
        proj = proj[:-len('@gentoo.org')]
    else:
        proj = proj.replace('@', '[at]')
    return '~~[%s (project)]~~' % proj


def main(ref_repo_path):
    GITHUB_DEV_MAPPING = os.environ['GITHUB_DEV_MAPPING']
    GITHUB_PROJ_MAPPING = os.environ['GITHUB_PROJ_MAPPING']
    GITHUB_USERNAME = os.environ['GITHUB_USERNAME']
    GITHUB_TOKEN_FILE = os.environ['GITHUB_TOKEN_FILE']
    GITHUB_REPO = os.environ['GITHUB_REPO']

    with open(GITHUB_TOKEN_FILE) as f:
        token = f.read().strip()

    g = github.Github(GITHUB_USERNAME, token, per_page=50)
    r = g.get_repo(GITHUB_REPO)

    with open(GITHUB_DEV_MAPPING) as f:
        dev_mapping = json.load(f)
    with open(GITHUB_PROJ_MAPPING) as f:
        proj_mapping = json.load(f)
    with open(os.path.join(ref_repo_path, 'profiles/categories')) as f:
        categories = [l.strip() for l in f.read().splitlines()]

    for pr in r.get_pulls(state='open'):
        # note: we need github.Issue due to labels missing in PR
        issue = r.get_issue(pr.number)
        assign_one(pr, issue, dev_mapping, proj_mapping, categories,
                GITHUB_USERNAME, ref_repo_path)

    return 0


def assign_one(pr, issue, dev_mapping, proj_mapping, categories,
        GITHUB_USERNAME, ref_repo_path):
    # check if assigned already
    if issue.assignee:
        print('PR#%d: assignee found' % pr.number)
        return
    for l in issue.get_labels():
        if l.name in ('assigned', 'need assignment', 'do not merge'):
            print('PR#%d: %s label found' % (pr.number, l.name))
            return

    # delete old results
    for co in issue.get_comments():
        if co.user.login == GITHUB_USERNAME:
            if 'Pull Request assignment' not in co.body:
                continue
            co.delete()

    # scan file list
    areas = set()
    packages = set()
    for f in pr.get_files():
        path = f.filename.split('/')
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
''' % (', '.join(sorted(areas)) or '(none, wtf?!)',
        ', '.join(sorted(packages)[0:5]) or '(none)',
        '...' if len(packages) > 5 else '')

    new_package = False
    maint_needed = False
    cant_assign = False
    not_self_maintained = False

    if packages:
        # now try to determine unique sets of maintainers
        # if we get too many unique sets, i.e. we would end up highlighting
        # everyone, do not auto-assign
        pkg_maints = {}
        unique_maints = set()
        for p in packages:
            ppath = os.path.join(ref_repo_path, p, 'metadata.xml')
            try:
                metadata_xml = lxml.etree.parse(ppath)
            except (OSError, IOError):
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
                    # if for at least one package, the user is not
                    # in maintainers, we do not consider it self-maintained
                    # TODO: handle team memberships
                    if '@' + pr.user.login not in all_ms:
                        not_self_maintained = True
                    unique_maints.add(tuple(sorted(all_ms)))
                    if len(unique_maints) > 5:
                        break
                else:
                    # maintainer-needed!
                    pkg_maints[p] = ['@gentoo/proxy-maint (maintainer needed)']
                    maint_needed = True

        if len(unique_maints) > 5:
            cant_assign = True
            body += '\n@gentoo/github: Too many disjoint maintainers, disabling auto-assignment.'
        else:
            for p in sorted(packages):
                body += '\n**%s**: %s' % (p, ', '.join(pkg_maints[p]))
            if cant_assign:
                body += '\n\nAt least one of the listed packages is maintained entirely by non-GitHub developers!'
    else:
        cant_assign = True
        body += '\n@gentoo/github'

    if maint_needed:
        issue.add_to_labels('maintainer-needed')
    if new_package:
        issue.add_to_labels('new package')
    if cant_assign:
        issue.add_to_labels('need assignment')
    else:
        if not not_self_maintained:
            issue.add_to_labels('self-maintained')
        issue.add_to_labels('assigned')
    issue.create_comment(body)
    print('PR#%d: assigned' % pr.number)


if __name__ == '__main__':
    try:
        sys.exit(main(*sys.argv[1:]))
    except socket.timeout:
        print('-- Exiting due to socket timeout --')
        sys.exit(0)
