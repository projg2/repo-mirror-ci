#!/bin/bash

set -e -x

repo=${GENTOO_CI_GIT}
borked_list=${repo}/borked.list
borked_last=${repo}/borked.last
warning_list=${repo}/warning.list
warning_last=${repo}/warning.last
blame_list=${repo}/blame
uri_prefix=${GENTOO_CI_URI_PREFIX}
mail_to=${GENTOO_CI_MAIL}
mail_cc=()
previous_commit=${1}
next_commit=${2}

subject=

# first, determine the state wrt warnings
if [[ ! -s ${warning_list} ]]; then
	if [[ -s ${warning_last} ]]; then
		subject="FIXED: all warnings have been fixed"
		mail="No way! We're clean as a pin!"
	fi
else
	if [[ ! -s ${warning_last} ]]; then
		subject="WARNING: new warnings for the repo!"
		mail="Looks like someone is doing nasty stuff!"
	elif ! cmp -s "${warning_list}" "${warning_last}"; then
		subject="WARNING: repository still has warnings!"
		mail="Looks like the warning list has just changed!"
	fi
fi

# then determine the state wrt errors (which are considered more
# important and therefore overwrite warnings statuses)
if [[ ! -s ${borked_list} ]]; then
	if [[ -s ${borked_last} ]]; then
		subject="FIXED: all failures have been fixed"
		mail="Everything seems nice and cool now."
	fi
else
	if [[ ! -s ${borked_last} ]]; then
		subject="BROKEN: repository became broken!"
		mail="Looks like someone just broke Gentoo!"
	elif ! cmp -s "${borked_list}" "${borked_last}"; then
		subject="BROKEN: repository is still broken!"
		mail="Looks like the breakage list has just changed!"
	elif [[ -n ${subject} ]]; then
		# if we have changes in warning list
		# if we have both warnings and errors but no changes in error
		# list, keep the error subject but give the warning message

		# the original message for FIXED doesn't fit when we have
		# errors
		if [[ ${subject} == FIXED* ]]; then
			mail="We've gotten rid of the warnings! Now focus on the errors!"
		fi
		subject="BROKEN: repository is still broken!"
	fi
fi

[[ ${subject} ]] || exit 0

current_rev=$(cd "${repo}"; git rev-parse --short HEAD)

fixed=()
old=()
new=()

while read t l; do
	case "${t}" in
		fixed) fixed+=( "${l}" );;
		old) old+=( "${l}" );;
		new) new+=( "${l}" );;
		*)
			echo "Invalid diff result: ${t} ${l}" >&2
			exit 1;;
	esac
done < <(diff -N \
		--old-line-format='fixed %L' \
		--unchanged-line-format='old %L' \
		--new-line-format='new %L' \
		"${borked_last}" "${borked_list}")

wfixed=()
wold=()
wnew=()

while read t l; do
	case "${t}" in
		fixed) wfixed+=( "${l}" );;
		old) wold+=( "${l}" );;
		new) wnew+=( "${l}" );;
		*)
			echo "Invalid diff result: ${t} ${l}" >&2
			exit 1;;
	esac
done < <(diff -N \
		--old-line-format='fixed %L' \
		--unchanged-line-format='old %L' \
		--new-line-format='new %L' \
		"${warning_last}" "${warning_list}")

broken_commits=()
cc_line=()

if [[ ( ${new[@]} || ${wnew[@]} ) && ${previous_commit} && $(( ${#new[@]} + ${#wnew[@]} )) -lt 50 ]]; then
	trap 'rm -rf "${BISECT_TMP}"' EXIT
	export BISECT_TMP=$(mktemp -d)
	mkdir -p "${BISECT_TMP}"/.config/pkgcore
	sed -e "s^@path@^${SYNC_DIR}/gentoo^" \
		"${SCRIPT_DIR}"/gentoo-ci/pkgcore.conf.in \
		> "${BISECT_TMP}"/.config/pkgcore/pkgcore.conf

	# check one commit extra to make sure the breakages were introduced
	# in the commit set; this could happen e.g. when new checks
	# are added on top of already-broken repo
	pre_previous_commit=$(cd "${SYNC_DIR}"/gentoo; git rev-parse "${previous_commit}^")
	flag=e
	set -- "${new[@]##*#}" -WARN- "${wnew[@]##*#}"
	while [[ ${@} ]]; do
		if [[ ${1} == -WARN- ]]; then
			flag=w
			shift
			continue
		fi

		commit=$("${SCRIPT_DIR}"/gentoo-ci/bisect-borked.bash \
			"${next_commit}" "${pre_previous_commit}" "${flag}" "${@}")
		pkg=${1}
		shift

		# skip breakages introduced before the commit set
		[[ ${pre_previous_commit} != ${commit}* ]] || continue

		# record the blame!
		echo "${pkg} ${commit}" >> "${blame_list}.${flag}"

		# skip duplicates
		for c in "${broken_commits[@]}"; do
			[[ ${c} != ${commit} ]] || continue 2
		done
		broken_commits+=( "${commit}" )

		for a in $(cd "${SYNC_DIR}"/gentoo; git log --pretty='%ae %ce' "${commit}" -1)
		do
			for o in "${mail_cc[@]}"; do
				[[ ${o} != ${a} ]] || continue 2
			done
			mail_cc+=( "${a}" )
			cc_line+=( "<${a}>" )
		done
	done

	trap '' EXIT
	rm -rf "${BISECT_TMP}"
fi

# CC people whose breakages have been fixed
if [[ ${fixed[@]} || ${wfixed[@]} ]]; then
	flag=e
	set -- "${fixed[@]##*#}" -WARN- "${wfixed[@]##*#}"
	while [[ ${@} ]]; do
		if [[ ${1} == -WARN- ]]; then
			flag=w
			shift
			continue
		fi

		while read pkg commit; do
			if [[ ${pkg} == ${1} ]]; then
				for a in $(cd "${SYNC_DIR}"/gentoo; git log --pretty='%ae %ce' "${commit}" -1)
				do
					for o in "${mail_cc[@]}"; do
						[[ ${o} != ${a} ]] || continue 2
					done
					mail_cc+=( "${a}" )
					cc_line+=( "<${a}>" )
				done

				sed -i -e "\@^${pkg}@d" "${blame_list}.${flag}"

				# we can't have more than one anyway
				break
			fi
		done < <( cat "${blame_list}.${flag}" || : )

		shift
	done
fi

cc_line=${cc_line[*]}

IFS='
'

# need to escape for the script
mail_new=${new//\//:}
mail_wnew=${wnew//\//:}

mail="Subject: ${subject}
To: <${mail_to}>
${mail_cc[@]:+CC: ${cc_line// /, }
}Content-Type: text/plain; charset=utf8

${mail}

${new:+New issues (${#new[@]}):
${mail_new[*]/#/
${uri_prefix}/${current_rev}/output.html;pkg=}


}${wnew:+New warnings (${#wnew[@]}):
${mail_wnew[*]/#/
${uri_prefix}/${current_rev}/output.html;pkg=}


}${fixed:+Issues fixed since last run (${#fixed[@]}):
${fixed[*]/#/
}


}${wfixed:+Warnings fixed since last run (${#wfixed[@]}):
${wfixed[*]/#/
}


}${broken_commits:+Introduced by commits:
${broken_commits[*]/#/
${GENTOO_CI_GITWEB_COMMIT_URI}}


}Changes since last check:
${GENTOO_CI_GITWEB_URI}${previous_commit}..${next_commit}


${old:+Previous issues still unfixed: ${#old[@]}
}${wold:+Previous warnings still unfixed: ${#wold[@]}
}

Current report:
${uri_prefix}


}--
Gentoo repository CI
https://wiki.gentoo.org/wiki/Project:Repository_mirror_and_CI"

sendmail "${mail_to}" "${mail_cc[@]}" <<<"${mail}"
cp "${borked_list}" "${borked_last}"
cp "${warning_list}" "${warning_last}"
if [[ -n ${new[@]} ]]; then
	"${SCRIPT_DIR}"/gentoo-ci/report-borked-irc.py "${mail_cc[*]}" \
		"${uri_prefix}/${current_rev}/output.html" \
		"${broken_commits[*]/#/${GENTOO_CI_GITWEB_COMMIT_URI}}"
fi
