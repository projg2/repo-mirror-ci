#!/bin/bash

. "$(dirname "${0}")"/repo-mirror-ci.conf

# SANITY!
export TZ=UTC

nolock=
if [[ ${1} == --nolock ]]; then
       nolock=1
       shift
fi

script=${1}
basename=${1##*/}
basename=${basename%.*}

exec {lockfd}>> "${CRONJOB_STATE_DIR}/${basename}.lock"
flock -x -n "${lockfd}" || exit 0

if [[ ! ${nolock} ]]; then
       exec {gentoolockfd}>> "${CRONJOB_STATE_DIR}/gentoo-repo.lock"
       flock -x "${gentoolockfd}" || exit 1
fi

exec &> "${CRONJOB_STATE_DIR}/${basename}.log"

start=$(date -u "+%Y-%m-%dT%H:%M:%SZ")
echo "Start: ${start}"
(
	. "${VIRTUAL_ENV}"/bin/activate
	. "${script}"
)
ret=${?}
stop=$(date -u "+%Y-%m-%dT%H:%M:%SZ")
echo "Stop: ${stop} (exited with ${ret})"

echo "${start} ${stop}" >> "${CRONJOB_STATE_DIR}/${basename}.times"

if [[ ${ret} -ne 0 ]]; then
	# close logs
	exec &>/dev/null

	# store a local copy of the log in case mail failed
	cp "${CRONJOB_STATE_DIR}/${basename}.log" \
	       "${CRONJOB_STATE_DIR}/${basename}.log.${start}"

	sendmail "${CRONJOB_ADMIN_MAIL}" <<-EOF
		Subject: ${basename} cronjob failure
		To: <${CRONJOB_ADMIN_MAIL}>
		Content-Type: text/plain; charset=utf8

		$(<"${CRONJOB_STATE_DIR}/${basename}.log")
	EOF
fi
