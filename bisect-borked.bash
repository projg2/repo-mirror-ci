#!/bin/bash

exec 3>&1
exec 1>&2

set -e -x

pkgs=( "${@:4}" )
bad=${1}
good=${2}
flag=${3}

cd "${SYNC_DIR}/gentoo"
initial_commit=$(git rev-parse HEAD)
trap "git bisect reset; [[ \$(git rev-parse HEAD) == '${initial_commit}' ]] || git checkout -q '${initial_commit}'" EXIT

git bisect start --no-checkout "${bad}" "${good}^"
git bisect run "${SCRIPT_DIR}"/bisect-run-pkgcheck.bash "${flag}" "${pkgs[@]}"
git rev-parse --short bisect/bad >&3
