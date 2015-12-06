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
Looks like someone just broke Gentoo! Please take a look
at the following pkgcheck failures:"
	elif [[ $(wc -l <"${borked_list}") -gt $(wc -l <"${borked_last}") ]]; then
		subject="BROKEN: repository is even more broken!"
		mail="
Looks like the breakage list has just grown! Please take a look
at the following pkgcheck failures:"
	elif [[ $(wc -l <"${borked_list}") -lt $(wc -l <"${borked_last}") ]]; then
		subject="BROKEN: repository is less broken now!"
		mail="
Looks like the breakage list has just shrinked! Good work, but please
fix the remaining pkgcheck failures:"
	elif ! cmp -s "${borked_list}" "${borked_last}"; then
		subject="BROKEN: repository is still broken!"
		mail="
Looks like the breakage list just changed! Please take a look
at the following pkgcheck failures:"
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
while read l; do
	mail+="${uri_prefix}/${current_rev}/${l}
"
done <"${borked_list}"

mail+="

Changes since last check:
${GENTOO_CI_GITWEB_URI}${previous_commit}..${next_commit}

--
Gentoo repository CI"

sendmail "${mail_to}" <<<"${mail}"
cp "${borked_list}" "${borked_last}"
