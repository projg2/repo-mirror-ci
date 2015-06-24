REPOSDIR = ~/repos
MIRRORDIR = ~/mirror

GITHUB_PREFIX = git@github.com:gentoo-mirror

include Makefile.repos

update: $(patsubst %,update-%,$(REPOS))
clean: $(patsubst %,clean-%,$(DELETED_REPOS))
force-push: $(patsubst %,push-%,$(REPOS))

update-%: $(MIRRORDIR)/% rsync-%
	cd $< && git add -A
	cd $< && { git diff --cached --quiet --exit-code || { git commit --quiet -m "$(shell date -u '+%F %T UTC')"; git push; }; }

push-%: $(MIRRORDIR)/%
	cd $< && git push

rsync-%: $(REPOSDIR)/% $(MIRRORDIR)/%
	rsync -rlpt --delete --exclude='.*/' $< $(MIRRORDIR)

$(MIRRORDIR)/%: create-%
	:

create-%:
	cd $(MIRRORDIR) && git clone $(GITHUB_PREFIX)/$(subst create-,,$@)

clean-%:
	cd $(MIRRORDIR) && rm -rf $(subst clean-,,$@)

.PHONY: update clean
