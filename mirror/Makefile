BINDIR = ~/bin
SYNCDIR = ~/sync
REPOSDIR = ~/repos
MIRRORDIR = ~/mirror

GITHUB_PREFIX = git@github.com:gentoo-mirror

include Makefile.repos

update: $(patsubst %,update-%,$(REPOS))
clean: $(patsubst %,clean-%,$(DELETED_REPOS))
force-push: $(patsubst %,push-%,$(REPOS))

update-%: $(MIRRORDIR)/% rsync-%
	cd $< && git add -A -f
	cd $< && { git diff --cached --quiet --exit-code || { LANG=C date -u "+%a, %d %b %Y %H:%M:%S +0000" > metadata/timestamp.chk && git add -f metadata/timestamp.chk && git commit --quiet -m "$(shell date -u '+%F %T UTC')" && git push; }; }

push-%: $(MIRRORDIR)/%
	cd $< && git push

merge-%: $(SYNCDIR)/% $(MIRRORDIR)/%
	$(BINDIR)/smart-merge.bash $< $(MIRRORDIR)/$(subst merge-,,$@) master

rsync-%: $(REPOSDIR)/% $(MIRRORDIR)/% merge-%
	rsync -rlpt --delete --exclude=metadata/timestamp.chk --exclude='.*/' $< $(MIRRORDIR)/

$(MIRRORDIR)/%: create-%
	:

create-%:
	cd $(MIRRORDIR) && git clone $(GITHUB_PREFIX)/$(subst create-,,$@)

clean-%:
	cd $(MIRRORDIR) && rm -rf $(subst clean-,,$@)

.PHONY: update clean
