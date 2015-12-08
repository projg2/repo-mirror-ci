#!/bin/bash

set -e -x

repo=${GENTOO_CI_GIT}
borked_list=${repo}/borked.list
borked_last=${repo}/borked.last
uri_prefix=${GENTOO_CI_URI_PREFIX}
mail_to=${GENTOO_CI_MAIL}
previous_commit=${1}
next_commit=${2}

if [[ ! -s ${borked_list} ]]; then
	if [[ -s ${borked_last} ]]; then
		subject="FIXED: all failures have been fixed"
		mail="
Everything seems nice and cool now."
	else
		exit 0
	fi
else
	if [[ ! -s ${borked_last} ]]; then
		subject="BROKEN: repository became broken!"
		mail="
Looks like someone just broke Gentoo!"
	elif ! cmp -s "${borked_list}" "${borked_last}"; then
		subject="BROKEN: repository is still broken!"
		mail="
Looks like the breakage list has just changed!"
	else
		exit 0
	fi
fi

mail="Subject: ${subject}
To: <${mail_to}>
Content-Type: text/plain; charset=utf8
${mail}

"

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

IFS='
'

mail+="
${new:+New issues:
${new[*]/#/${uri_prefix}/${current_rev}/}


}${old:+Previous issues still unfixed:
${old[*]/#/${uri_prefix}/${current_rev}/}


}${fixed:+Packages fixed since last run:
${fixed[*]/#/${uri_prefix}/${current_rev}/}


}Changes since last check:
${GENTOO_CI_GITWEB_URI}${previous_commit}..${next_commit}

--
Gentoo repository CI"

echo "$mail"
exit 1

sendmail "${mail_to}" <<<"${mail}"
cp "${borked_list}" "${borked_last}"
