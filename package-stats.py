#!/usr/bin/env python

import pkgcore.config


def iter_pkgs(repo):
    for cat, pns in repo.packages.items():
        if not cat:
            continue
        for pn in pns:
            yield '/'.join((cat, pn))


def print_results(rdict):
    num_print = 25

    for k, v in sorted(rdict.items(), key=lambda kv: kv[1], reverse=True)[:num_print]:
        # ::gentoo forks may have 0
        if v == 0:
            break
        print('%3d %s' % (v, k))


def main():
    c = pkgcore.config.load_config()
    d = c.get_default('domain')

    new_stats = {}
    gentoo_fork_stats = {}

    # collect list of ::gentoo packages
    for pkg in iter_pkgs(d.repos_raw['gentoo']):
        gentoo_fork_stats[pkg] = 0

    # collect list of slave repo packages
    for r in d.ebuild_repos_raw:
        rr = r.raw_repo
        # skip non-slave repos to avoid counting ::gentoo and ::gentoo forks
        if not rr.masters:
            continue

        for pkg in iter_pkgs(rr):
            if pkg in gentoo_fork_stats:
                # packages in ::gentoo are counted as forks
                gentoo_fork_stats[pkg] += 1
            else:
                # other packages are counted as new
                if pkg not in new_stats:
                    new_stats[pkg] = 0
                new_stats[pkg] += 1

    # print results
    print('== Most common new packages ==')
    print_results(new_stats)
    print()
    print('== Most common ::gentoo forked packages ==')
    print_results(gentoo_fork_stats)


if __name__ == '__main__':
    main()
