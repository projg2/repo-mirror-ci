# vim:ft=make
jobs = 0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 global
out_xml = $(patsubst %,%.xml,$(jobs))
jobs_no = 16
repo = $(REPOS_DIR)/gentoo
checker = $(SCRIPT_DIR)/shared-ci/run-pkgcheck.bash

HOME = $(GENTOO_CI_GIT)

all: output.xml

output.xml: $(out_xml)
	python3 $(PKGCHECK_RESULT_PARSER_GIT)/combine-xml.py $(out_xml) > output.xml
	rm -f $(out_xml)

%.xml:
	{ cd $(repo) && bash $(checker) $(patsubst %.xml,%,$@) $(jobs_no); } > $@

clean:
	rm -f *.xml

.PHONY: all clean
