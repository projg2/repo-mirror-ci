#!/bin/bash
set -e -x

JOB=${1}
NO_JOBS=${2}

COMMON=(
	-r gentoo --reporter XmlReporter
	-p stable,dev
)
SKIPPED_CHECKS=(
	-c=-ImlateReport,-UnstableOnlyReport,-DeprecatedEAPIReport,-DeprecatedEclassReport,-RedundantVersionReport
)

if [[ ! ${JOB} || ! ${NO_JOBS} ]]; then
	# simple whole-repo run
	exec pkgcheck scan "${COMMON[@]}" "${SKIPPED_CHECKS[@]}"
elif [[ ${JOB} == global ]]; then
	# global check part of split run
	exec pkgcheck scan "${COMMON[@]}" \
		-C repo
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

	exec pkgcheck scan "${COMMON[@]}" "${cats[@]}" -C non-repo "${SKIPPED_CHECKS[@]}"
fi
