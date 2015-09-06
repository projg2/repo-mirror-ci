#!/bin/bash

exec {lockfd}>> /home/mgorny/gentoo-ci.lock
flock -x -n "${lockfd}" || exit 0

exec {gentoolockfd}>> /home/mgorny/gentoo-repo.lock
flock -x "${gentoolockfd}" || exit 1

exec &> /home/mgorny/gentoo-ci.log
set -e -x

ulimit -t 600 -v 2097152
date -u

. /home/mgorny/pkgcore-venv/bin/activate

cd /home/mgorny/sync/gentoo
ts=$(git log --pretty='%ct' -1)
touch -r /home/mgorny/mirror/gentoo/metadata/timestamp.chk .git/timestamp
cd /home/mgorny/gentoo-ci
time timeout 15m make -j16
/home/mgorny/bin/txt2html-gentoo.py /home/mgorny/repos/gentoo "${ts}" *.txt
git add *.txt *.html *.css
git diff --cached --quiet --exit-code || git commit -m "$(date -u --date="@$(cd /home/mgorny/sync/gentoo; git log --pretty="%ct" -1)" "+%Y-%m-%d %H:%M:%S UTC")"
git push
/home/mgorny/bin/report-borked.bash

date -u
