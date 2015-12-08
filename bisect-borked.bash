#!/bin/bash

set -e -x

exec 3>&1
exec >&2

pkg=${1}
bad=${2}
good=${3}

trap 'rm -rf "${BISECT_TMP}"' EXIT
export BISECT_TMP=$(mktemp -d)
sed -e "s^@path@^${SYNC_DIR}/gentoo^" \
	"${TRAVIS_REPO_CHECKS_GIT}"/pkgcore.conf.in \
	> "${BISECT_TMP}"/.pkgcore.conf

cd "${SYNC_DIR}/gentoo"
trap 'git bisect reset; rm -rf "${BISECT_TMP}"' EXIT

bad_commit=
git bisect start "${bad}" "${good}"
set +x
while read first second; do
	echo "${first} ${second}"
	[[ ${first} == commit ]] && bad_commit=${second}
done < <(git bisect run "${SCRIPT_DIR}"/bisect-run-pkgcheck.bash "${pkg}")

git rev-parse --short "${bad_commit}" >&3
