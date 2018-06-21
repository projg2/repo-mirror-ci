#!/bin/bash

set -e -x

remaining=(
	${GPG_EXTRA_KEYS}
	$(ldapsearch '(&(gentooAccess=git.gentoo.org/repo/gentoo.git)(gentooStatus=active))' \
		-Z gpgfingerprint -LLL \
		| sed -n -e '/^gpgfingerprint: /{s/^.*://;s/ //g;p}' \
		| sort -u)
)

export GNUPGHOME=~/gnupg.tmp

rm -f -r "${GNUPGHOME}"
mkdir "${GNUPGHOME}"

while :; do
	gpg --recv-keys "${remaining[@]}" || :
	missing=()
	for key in "${remaining[@]}"; do
		gpg --list-public "${key}" &>/dev/null || missing+=( "${key}" )
	done

	[[ ${#missing[@]} -ne 0 ]] || break

	# fail if we did not make progress
	[[ ${#missing[@]} -ne ${#remaining[@]} ]]

	remaining=( "${missing[@]}" )
done

mv "${GNUPGHOME}"/pubring.kbx ~/.gnupg
rm -f -r "${GNUPGHOME}"

unset GNUPGHOME
gpg --update-trustdb
