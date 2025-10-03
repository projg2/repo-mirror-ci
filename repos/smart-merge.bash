#!/bin/bash
set -e -x

repo=${1}
mirror=${2}
m_branch=${3}

[[ ${repo} && ${mirror} && ${m_branch} ]]

# no git, no fun
[[ -d ${repo}/.git ]] || exit 0

cd -- "${repo}"
branch=$(git symbolic-ref -q --short HEAD)
[[ ${branch} ]] || exit 0

cd -- "${mirror}"
git fetch -- "${repo}" "+${branch}:refs/orig/${branch}"
if git merge-base -- "${m_branch}" "refs/orig/${branch}" > /dev/null; then
	# regular update
	if ! git merge -q -s recursive -X theirs -m "Merge updates from ${branch}" -- "refs/orig/${branch}"; then
		# check for conflicts
		conflicts=no
		while read st filename rest; do
			case "${st}" in
				DD|AU|UD|UA|DU|AA|UU)
					# be lazy, handle all merge conflicts via rm...
					git rm --cached -- "${filename}"
					conflicts=yes
					;;
				*)
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
	git merge -q --ff -- "refs/orig/${branch}"
else
	# repo rewrite
	git checkout -q -- "refs/orig/${branch}"
	git merge -q -s ours --allow-unrelated-histories \
		-m "Merge/replace with the new version of ${branch} (reversed 'ours' strategy)" \
		-- "${m_branch}"
	git branch -f -- "${m_branch}" HEAD
	git checkout -- "${m_branch}"
fi
