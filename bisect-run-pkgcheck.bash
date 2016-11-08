#!/bin/bash

set -e -x

trap 'exit 255' EXIT

export HOME=${BISECT_TMP}
current_commit=$(git rev-parse BISECT_HEAD)

if [[ -s ${BISECT_TMP}/.bisect.cache ]]; then
	while read -a cline; do
		if [[ ${cline[0]} == ${current_commit} ]]; then
			ret=0
			for p in "${cline[@]:1}"; do
				if [[ ${p} == ${1} ]]; then
					ret=1
					break
				fi
			done
			trap '' EXIT
			exit "${ret}"
		fi
	done <"${BISECT_TMP}/.bisect.cache"
fi

git checkout -q "${current_commit}"

# we always check multiple packages and cache the result to avoid
# re-checking the same commits in next bisect
# however, we only return result for the first one

pkgcheck -r gentoo --reporter XmlReporter "${@}" \
	--glsa-dir "${MIRROR_DIR}"/gentoo/metadata/glsa \
	${PKGCHECK_OPTIONS} \
	> "${BISECT_TMP}/.bisect.tmp.xml"

"${PKGCHECK_RESULT_PARSER_GIT}"/xml2html.py \
	--output /dev/null --borked "${BISECT_TMP}/.bisect.tmp.borked" \
	"${BISECT_TMP}/.bisect.tmp.xml"

borked_pkgs=()
while read l; do
	borked_pkgs+=( "${l##*#}" )
done <"${BISECT_TMP}/.bisect.tmp.borked"

echo "${current_commit} ${borked_pkgs[*]}" >> "${BISECT_TMP}/.bisect.cache"

ret=0
for p in "${borked_pkgs[@]}"; do
	if [[ ${1} == ${p} ]]; then
		ret=1
		break
	fi
done

trap '' EXIT
exit "${ret}"
