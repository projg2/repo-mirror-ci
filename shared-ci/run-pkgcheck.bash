#!/bin/bash
set -e -x

JOB=${1}
NO_JOBS=${2}

if [[ ${JOB} == global ]]; then
	# global check part of split run
	exec pkgcheck scan -r gentoo --reporter XmlReporter \
		${PKGCHECK_GLOBAL_SCAN_OPTIONS}
else
	# keep the category scan silent, it's too verbose
	set +x
	cats=()
	if [[ -s $(dirname "${0}")/cats/cats.${JOB} ]]; then
		for c in $(<"$(dirname "${0}")"/cats/cats.${JOB})
		do
			cats+=( "${c}/*" )
		done
	else
		cats=( nonexist/nonexist )
	fi

	if [[ ${JOB} -eq $(( NO_JOBS - 1 )) ]]; then
		# (ideally empty)
		cats+=( $(sort profiles/categories | comm -23 - "$(dirname "${0}")"/cats.sorted) )
	fi
	set -x

	exec pkgcheck scan -r gentoo --reporter XmlReporter \
		${PKGCHECK_CAT_SCAN_OPTIONS} "${cats[@]}"
fi
