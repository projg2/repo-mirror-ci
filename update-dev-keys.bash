#!/bin/bash

set -e -x

remaining=(
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

	[[ ${#missing[@]} -ne 0 && ${#missing[@]} -ne ${#remaining[@]} ]] || break
	remaining=( "${missing[@]}" )
done

gpg --import ~/repo-mirror-ci.key
mv "${GNUPGHOME}"/pubring.kbx ~/.gnupg
