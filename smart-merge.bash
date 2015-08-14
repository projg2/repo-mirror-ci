#!/bin/bash
set -e -x

repo=${1}
mirror=${2}
branch=${3}

[[ ${repo} && ${mirror} && ${branch} ]]

# no git, no fun
[[ -d ${repo}/.git ]] || exit 0

cd "${mirror}"
git fetch "${repo}" "${branch}:refs/orig/${branch}"
if git merge-base "${branch}" "refs/orig/${branch}" > /dev/null; then
	# regular update
	git merge -q -s recursive -X theirs -m "Merge updates from ${branch}" "refs/orig/${branch}"
elif ! git rev-parse HEAD &>/dev/null; then
	# empty repo
	git merge -q --ff "refs/orig/${branch}"
else
	# repo rewrite
	git checkout -q "refs/orig/${branch}"
	git merge -q -s ours -m "Merge/replace with the new version of ${branch} (reversed 'ours' strategy)" "${branch}"
	git branch -f "${branch}" HEAD
	git checkout "${branch}"
fi
