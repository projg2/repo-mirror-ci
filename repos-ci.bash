#!/bin/bash
# run repos & CI combined

timeout 120m "${SCRIPT_DIR}"/repos/repos.bash &&
	"${SCRIPT_DIR}"/gentoo-ci/gentoo-ci.bash
