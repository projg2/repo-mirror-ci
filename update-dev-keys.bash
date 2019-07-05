#!/bin/bash

set -e -x
cd

before=$(cksum committing-devs.gpg || :)
wget -N https://qa-reports.gentoo.org/output/committing-devs.gpg
after=$(cksum committing-devs.gpg || :)

[[ ${before} == ${after} ]] && exit 0

export GNUPGHOME=~/gnupg.tmp

rm -f -r "${GNUPGHOME}"
mkdir "${GNUPGHOME}"
cp committing-devs.gpg "${GNUPGHOME}"/pubring.gpg

[[ ! ${GPG_EXTRA_KEYS} ]] || gpg --no-auto-check-trustdb --keyserver hkps://keys.gentoo.org --recv-keys ${GPG_EXTRA_KEYS}

mv "${GNUPGHOME}"/pubring.gpg ~/.gnupg
rm -f -r "${GNUPGHOME}"

unset GNUPGHOME
gpg --update-trustdb
