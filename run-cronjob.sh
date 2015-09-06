#!/bin/bash

script=${1}
basename=${1##*/}
basename=${basename%.*}

exec {lockfd}>> /home/mgorny/"${basename}.lock"
flock -x -n "${lockfd}" || exit 0

exec {gentoolockfd}>> /home/mgorny/gentoo-repo.lock
flock -x "${gentoolockfd}" || exit 1

exec &> /home/mgorny/"${basename}.log"

start=$(date -u "+%Y-%m-%dT%H:%M:%SZ")
echo "Start: ${start}"
"${SHELL}" "${script}"
ret=${?}
stop=$(date -u "+%Y-%m-%dT%H:%M:%SZ")
echo "Stop: ${stop} (exited with ${ret})"

echo "${start} ${stop}" >> /home/mgorny/"${basename}.times"

# TODO: report errors
