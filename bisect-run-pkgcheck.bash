#!/bin/bash

set -e -x

trap 'exit 255' EXIT

export HOME=${BISECT_TMP}

pkgcheck -r gentoo --reporter XmlReporter "${1}" \
	-d imlate -d unstable_only -d cleanup -d stale_unstable \
	-d deprecated -d UnusedGlobalFlags -d UnusedLicense \
	-d CategoryMetadataXmlCheck \
	--profile-disable-dev --profile-disable-exp \
	> "${BISECT_TMP}/.bisect.tmp.xml"

"${PKGCHECK_RESULT_PARSER_GIT}"/xml2html.py \
	--output /dev/null --borked "${BISECT_TMP}/.bisect.tmp.borked" \
	"${BISECT_TMP}/.bisect.tmp.xml"

if grep -q "#${1}$" "${BISECT_TMP}/.bisect.tmp.borked"; then
	ret=1
else
	ret=0
fi

trap '' EXIT
exit "${ret}"
