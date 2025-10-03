#!/bin/bash
set -e -x

repo=${1}
mirror=${2}
m_branch=${3}

[[ ${repo} && ${mirror} && ${m_branch} ]]

# no git, no fun
[[ -d ${repo}/.git ]] || exit 0

cd -- "${mirror}"
[[ -z $(git diff --cached --name-only -- "orig/${m_branch}" |
	grep -E -v '^metadata/(dtd/|glsa/|md5-cache/|news/|pkg_desc_index|projects.xml|timestamp|xml-schema/)' |
	grep -v '^profiles/use.local.desc') ]]
