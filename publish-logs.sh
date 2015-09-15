#!/bin/bash

set -e -x

bindir=${SCRIPT_DIR}
datadir=${SCRIPT_DIR}
target=${REPORT_REPOS_GIT}
logdir=${1}
date=${logdir##*/}

[[ -d ${logdir} ]]

rm -f "${target}"/*
cp "${logdir}"/* "${target}"/
cp "${datadir}"/{log,repo-status}.css "${target}"/

cd "${target}"
"${bindir}"/txt2html.py *.txt
"${bindir}"/summary2html.py summary.json
git add *
git commit -a -m "${date}"
git push
