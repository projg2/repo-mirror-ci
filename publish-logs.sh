#!/bin/bash

set -e -x

bindir=~/bin
datadir=~/bin
target=~/git/repo-qa-check-results
logdir=${1}
date=${logdir##*/}

[[ -d ${logdir} ]]

rm -f "${target}"/*
cp "${logdir}"/* "${target}"/
cp "${datadir}"/{log,repo-status}.css "${target}"/

cd "${target}"
"${bindir}"/txt2html.py *.txt
"${bindir}"/summary2html.py > index.html
git add *
git commit -a -m "${date}"
git push
