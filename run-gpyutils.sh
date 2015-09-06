#!/bin/bash

exec {lockfd}>> /home/mgorny/gpyutils.lock
flock -x -n "${lockfd}" || exit 0

exec {gentoolockfd}>> /home/mgorny/gentoo-repo.lock
flock -x "${gentoolockfd}" || exit 1

exec &> /home/mgorny/gpyutils.log
set -e -x

ulimit -t 1200 -v 2097152
date -u

export PORTAGE_CONFIGROOT=/home/mgorny/data
cd /home/mgorny/git/gpyutils
timeout 20m make -j all
make push

date -u
