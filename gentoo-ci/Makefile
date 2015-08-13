jobs = 0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 global
jobs_no = 16
repo = /home/mgorny/repos/gentoo
checker = /home/mgorny/git/travis-repo-checks/run-pkgcheck.bash
ts = $(repo)/.git/timestamp

HOME = /home/mgorny/gentoo-ci

all: $(patsubst %,%.txt,$(jobs))

%.txt: $(ts)
	{ cd $(repo) && bash $(checker) $(patsubst %.txt,%,$@) $(jobs_no); } > $@ 2>&1

clean:
	rm -f *.txt

.PHONY: all
