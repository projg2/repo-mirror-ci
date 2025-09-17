#!/bin/bash

set -e -x
ulimit -t 800

# SANITY!
export TZ=UTC

date=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

mkdir -p "${CONFIG_ROOT}" "${CONFIG_ROOT_MIRROR}" "${CONFIG_ROOT_SYNC}" \
	"${SYNC_DIR}" "${MIRROR_DIR}" "${REPOS_DIR}"
for d in "${CONFIG_ROOT}" "${CONFIG_ROOT_MIRROR}" "${CONFIG_ROOT_SYNC}"
do
	# populate with necessary files
	mkdir -p -- "${d}"/etc/portage
	if [[ ! -e ${d}/etc/portage/make.profile ]]; then
		rm -f -- "${d}"/etc/portage/make.profile
		cp -d /etc/portage/make.profile "${d}"/etc/portage
	fi
	if [[ ! -e ${d}/etc/portage/make.conf ]]; then
		cp /etc/portage/make.conf "${d}"/etc/portage
	fi
done

cd -- "${REPORT_REPOS_GIT}"
rm -f -- *.txt *.css *.json *.html
cp "${SCRIPT_DIR}"/repos/data/{log,repo-status}.css \
	./"${SCRIPT_DIR}"/repos/update-repos.py

"${SCRIPT_DIR}"/repos/update-mirror.py summary.json \
	> "${MIRROR_DIR}"/Makefile.repos

"${SCRIPT_DIR}"/repos/txt2html.py *.txt
"${SCRIPT_DIR}"/repos/summary2html.py summary.json
git add -- *
git commit -a -m "${date}"
git push
curl "https://qa-reports-cdn-origin.gentoo.org/cgi-bin/trigger-pull.cgi?repos" || :

make -f "${SCRIPT_DIR}"/repos/mirror.make -C "${MIRROR_DIR}" clean
make -f "${SCRIPT_DIR}"/repos/mirror.make -j16 -O -k -C "${MIRROR_DIR}"
