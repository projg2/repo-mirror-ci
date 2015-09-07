#!/bin/bash
set -e -x

repo=${1}
mirror=${2}
branch=${3}

[[ ${repo} && ${mirror} && ${branch} ]]

# no git, no fun
[[ -d ${repo}/.git ]] || exit 0

cd "${mirror}"
git fetch "${repo}" "+${branch}:refs/orig/${branch}"
if git merge-base "${branch}" "refs/orig/${branch}" > /dev/null; then
	# regular update
	if ! git merge -q -s recursive -X theirs -m "Merge updates from ${branch}" "refs/orig/${branch}"; then
		# check for conflicts
		conflicts=no
		while read st filename rest; do
			case "${st}" in
				DD|AU|UD|UA|DU|AA|UU)
					# be lazy, handle all merge conflicts via rm...
					git rm --cached "${filename}"
					conflicts=yes
					;;
			esac
		done < <(git status --porcelain --untracked-files=no)
		if [[ ${conflicts} == yes ]]; then
			git commit -q -m "Merge updates from ${branch}"
		else
			echo "** git merge failed, no conflicts found" >&2
			exit 1
		fi
	fi
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
