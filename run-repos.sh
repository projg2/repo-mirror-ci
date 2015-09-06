#!/bin/bash

exec {lockfd}>> /home/mgorny/repos.lock
flock -x -n "${lockfd}" || exit 0

exec {gentoolockfd}>> /home/mgorny/gentoo-repo.lock
flock -x "${gentoolockfd}" || exit 1

exec &> /home/mgorny/repos.log
set -e -x

ulimit -t 600 -v 2097152
date -u

. /home/mgorny/pkgcore-venv/bin/activate

cd /home/mgorny
/home/mgorny/bin/update-repos.py
cd log
dates=( * )

/home/mgorny/bin/update-mirror.py "${dates[-1]}"/summary.json "${dates[-1]}"/repositories.xml > /home/mgorny/mirror/Makefile.repos
/home/mgorny/bin/publish-logs.sh ${dates[-1]}

make -C /home/mgorny/mirror clean
make -j16 -k -C /home/mgorny/mirror

date -u
