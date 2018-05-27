#!/bin/bash

set -e -x

remaining=( $(ssh dev.gentoo.org | sed -e 's/\r$//') )
export GNUPGHOME=~/gnupg.tmp

rm -f -r "${GNUPGHOME}"
mkdir "${GNUPGHOME}"

while :; do
	gpg --recv-keys "${remaining[@]}"
	missing=()
	for key in "${remaining[@]}"; do
		gpg --list-public "${key}" &>/dev/null || missing+=( "${key}" )
	done

	[[ ${#missing[@]} -ne 0 && ${#missing[@]} -ne ${#remaining[@]} ]] || break
	remaining=( "${missing[@]}" )
done

gpg --import ~/repo-mirror-ci.key
mv "${GNUPGHOME}"/pubring.kbx ~/.gnupg
