#!/bin/bash

set -e -x

borked_list=/home/mgorny/gentoo-ci/borked.list
borked_last=${borked_list%.list}.last
uri_prefix=https://gentoo.github.io/gentoo-qa-results/
mail_to=travis-ci@gentoo.org
reply_to=mgorny@gentoo.org

if [[ ! -f ${borked_list} ]]; then
	if [[ -f ${borked_last} ]]; then
		subject="[gentoo-ci] FIXED: all failures have been fixed"
		mail="
Everything seems nice and cool now."
	else
		exit 0
	fi
else
	if [[ ! -f ${borked_last} ]]; then
		subject="[gentoo-ci] BROKEN: repository became broken!"
		mail="
Looks like someone just broke Gentoo! Please take a look
at the following pkgcheck failures:"
	elif [[ $(wc -l <"${borked_list}") -gt $(wc -l <"${borked_last}") ]]; then
		subject="[gentoo-ci] BROKEN: repository is even more broken!"
		mail="
Looks like the breakage list has just grown! Please take a look
at the following pkgcheck failures:"
	elif [[ $(wc -l <"${borked_list}") -lt $(wc -l <"${borked_last}") ]]; then
		subject="[gentoo-ci] BROKEN: repository is less broken now!"
		mail="
Looks like the breakage list has just shrinked! Good work, but please
fix the remaining pkgcheck failures:"
	else
		exit 0
	fi
fi

mail="Subject: ${subject}
To: <${mail_to}>
Reply-To: <${reply_to}>
Content-Type: text/plain; charset=utf8
${mail}

"

while read l; do
	mail+="${uri_prefix}${l}
"
done <"${borked_list}"

mail+="
--
Gentoo repository CI"

sendmail "${mail_to}" <<<"${mail}"
cp "${borked_list}" "${borked_last}"
