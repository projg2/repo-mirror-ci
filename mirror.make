# vim:ft=make

BINDIR = $(SCRIPT_DIR)
SYNCDIR = $(SYNC_DIR)
REPOSDIR = $(REPOS_DIR)
MIRRORDIR = $(MIRROR_DIR)

GITHUB_PREFIX = git@github.com:gentoo-mirror

include $(MIRROR_DIR)/Makefile.repos

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

postmerge-%: $(MIRRORDIR)/% merge-%
	[ ! -f $(BINDIR)/repo-postmerge/$(subst postmerge-,,$@) ] || $(BINDIR)/repo-postmerge/$(subst postmerge-,,$@) $<

# TODO: projects.xml can come out of repo too
rsync-%: $(REPOSDIR)/% $(MIRRORDIR)/% merge-% postmerge-%
	rsync -rlpt --delete --exclude=metadata/timestamp.chk --exclude='.*/' --exclude=metadata/dtd --exclude=metadata/herds.xml --exclude=metadata/projects.xml --exclude=metadata/glsa --exclude=metadata/news $< $(MIRRORDIR)/

$(MIRRORDIR)/%: create-%
	:

create-%:
	cd $(MIRRORDIR) && git clone $(GITHUB_PREFIX)/$(subst create-,,$@)

clean-%:
	cd $(MIRRORDIR) && rm -rf $(subst clean-,,$@)

.PHONY: update clean
