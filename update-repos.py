#!/usr/bin/env python2.7
#  vim:se fileencoding=utf8
# (c) 2015 Michał Górny
# note: 2.7 needed because of pkgcore, awesome

try:
    import configparser
except ImportError:
    import ConfigParser as configparser

import datetime
import json
import os
import os.path
import pickle
import shutil
import subprocess
import sys
import time

from layman.api import LaymanAPI
from layman.config import BareConfig

CONFIG_ROOT = '/home/mgorny/data'
CONFIG_FILE = '/home/mgorny/config/layman.cfg'
LOG_DIR = '/home/mgorny/log'
REPOS_CONF = os.path.join(CONFIG_ROOT, 'etc', 'portage', 'repos.conf')

MAX_SYNC_JOBS = 32
MAX_REGEN_JOBS = 16
MAX_PCHECK_JOBS = 24
REGEN_THREADS = '2'

# repositories which are broken and take a lot of time to sync
BANNED_REPOS = frozenset(['chromiumos', 'udev'])

try:
    DEVNULL = subprocess.DEVNULL
except AttributeError:
    DEVNULL = open('/dev/null', 'r')

class State(object):
    # removed (no longer exists remotely)
    REMOVED = 'REMOVED'
    # unsupported repo type
    UNSUPPORTED = 'UNSUPPORTED'
    # unable to sync
    SYNC_FAIL = 'SYNC_FAIL'
    # empty repository (no files at all)
    EMPTY = 'EMPTY'
    # missing repo_name
    MISSING_REPO_NAME = 'MISSING_REPO_NAME'
    # conflicting repo_name
    CONFLICTING_REPO_NAME = 'CONFLICTING_REPO_NAME'
    # missing masters
    MISSING_MASTERS = 'MISSING_MASTERS'
    # invalid masters
    INVALID_MASTERS = 'INVALID_MASTERS'
    # invalid metadata (?)
    INVALID_METADATA = 'INVALID_METADATA'
    # bad cache
    BAD_CACHE = 'BAD_CACHE'
    # good
    GOOD = 'GOOD'


class SkipRepo(Exception):
    pass


class SourceMapping(object):
    """ Map layman repository info to repos.conf """

    def Git(self, uri, branch):
        if branch:
            raise SkipRepo('Git branches not supported')
        return {
            'sync-type': 'git',
            'sync-depth': '0',
            'sync-uri': uri,
        }

    def Mercurial(self, uri, branch):
        raise SkipRepo('Mercurial not supported')

    def Rsync(self, uri, branch):
        raise SkipRepo('RSync is broken in emaint sync (works with Gentoo repo only)')
        if branch:
            raise SkipRepo('Branches in rsync, wtf?!')
        return {
            'sync-type': 'rsync',
            'sync-uri': uri,
        }

    def Subversion(self, uri, branch):
        if branch:
            raise SkipRepo('Svn branches not supported')
        return {
            'sync-type': 'svn',
            'sync-uri': uri,
        }

    def Bzr(self, uri, branch):
        raise SkipRepo('Bzr not supported')


def can_pmaint(repos_conf, r):
    """ Check if repository can be synced using pmaint """
    # initial clone? can't do
    if not os.path.exists(repos_conf.get(r, 'location')):
        return False
    if repos_conf.get(r, 'sync-type') not in ('cvs', 'git', 'svn'):
        return False
    return True


class LoggerProxy(object):
    def __init__(self, logdir, key):
        self._path = os.path.join(logdir, key + '.txt')
        self._key = key

    def status(self, msg):
        sys.stderr.write('[%s] %s\n' % (self._key, msg))
        with open(self._path, 'a') as f:
            f.write(' * %s\n' % msg)

    def command(self, cmd):
        with open(self._path, 'a') as f:
            f.write('$ %s\n' % ' '.join(cmd))

    def open(self):
        return open(self._path, 'a')


class Logger(object):
    def __init__(self):
        dt = datetime.datetime.utcnow()
        self.log_dir = os.path.join(LOG_DIR, dt.strftime('%Y-%m-%dT%H:%M:%S'))
        os.makedirs(self.log_dir)

    def __getitem__(self, key):
        return LoggerProxy(self.log_dir, key)

    def write_summary(self, data):
        with open(os.path.join(self.log_dir, 'summary.json'), 'w') as f:
            json.dump(data, f)


class LazySubprocess(object):
    def __init__(self, log, *args, **kwargs):
        self._log = log
        self._args = args
        self._kwargs = kwargs
        self._s = None
        self._running = False

    def start(self):
        kwargs = self._kwargs
        self._log.command(self._args[0])
        with self._log.open() as f:
            kwargs['stdin'] = DEVNULL
            kwargs['stdout'] = f
            kwargs['stderr'] = subprocess.STDOUT
            self._s = subprocess.Popen(*self._args, **kwargs)
        self._running = True

    @property
    def running(self):
        return self._running

    def poll(self):
        assert(self._running)
        return self._s.poll()


class TaskManager(object):
    def __init__(self, max_jobs, log):
        self._max_jobs = max_jobs
        self._jobs = {}
        self._queue = []
        self._results = {}
        self._log = log

    def add(self, name, *args, **kwargs):
        subp = LazySubprocess(self._log[name], *args, **kwargs)
        if len(self._jobs) < self._max_jobs:
            subp.start()
            self._jobs[name] = subp
        else:
            self._queue.append((name, subp))

    def wait(self):
        while self._jobs or self._queue:
            to_del = []
            for n, s in self._jobs.items():
                ret = s.poll()
                if ret is not None:
                    self._results[n] = ret
                    yield (n, ret)
                    to_del.append(n)
            for n in to_del:
                del self._jobs[n]

            while len(self._jobs) < self._max_jobs and self._queue:
                n, s = self._queue.pop(0)
                s.start()
                self._jobs[n] = s
            
            time.sleep(0.25)

    def get_result(self, r):
        return self._results[r]


def main():
    log = Logger()
    config = BareConfig(config=CONFIG_FILE, read_configfile=True)
    reposdir = config['storage']
    layman = LaymanAPI(config=config)
    states = {}

    os.environ['PORTAGE_CONFIGROOT'] = CONFIG_ROOT

    # collect all local and remote repositories
    print('* fetching repository list')
    layman.fetch_remote_list()
    remote_repos = frozenset(layman.get_available())
    remote_repos = remote_repos.difference(BANNED_REPOS)
    remote_info = layman.get_all_info(remote_repos)

    # collect local repository configuration
    print('* updating repos.conf')
    repos_conf = configparser.ConfigParser()
    repos_conf.read([REPOS_CONF])
    local_repos = frozenset(repos_conf.sections())

    # 1. remove repos that no longer exist
    to_remove = list(local_repos.difference(remote_repos))
    for r in sorted(to_remove):
        states[r] = {'x-state': State.REMOVED}
        log[r].status('Removing, no longer on remote list')
        repos_conf.remove_section(r)

    # 2. update URIs for local repos, add new repos
    srcmap = SourceMapping()
    existing_repos = []
    for r, data in sorted(remote_info.items()):
        states[r] = dict(data)
        del states[r]['src_types']
        del states[r]['src_uris']
        for src_uri, src_type, src_branch in data['sources']:
            try:
                vals = getattr(srcmap, src_type)(src_uri, src_branch)
            except SkipRepo as e:
                log[r].status('Skipping %s: %s' % (src_uri, str(e)))
            else:
                break
        else:
            states[r]['x-state'] = State.UNSUPPORTED
            if repos_conf.has_section(r):
                repos_conf.remove_section(r)
                to_remove.append(r)
            continue

        if not repos_conf.has_section(r):
            log[r].status('Adding new repository')
            repos_conf.add_section(r)
        repo_path = os.path.join(reposdir, r)
        repos_conf.set(r, 'location', repo_path)

        if os.path.exists(repo_path):
            # check whether sync params changed
            for k, v in vals.items():
                if not repos_conf.has_option(r, k) or repos_conf.get(r, k) != v:
                    log[r].status('Resetting, sync parameters changed')
                    to_remove.append(r)
                    break
            else:
                existing_repos.append(r)

        for k, v in vals.items():
            repos_conf.set(r, k, v)

    # 3. write new repos.conf, remove stale checkouts
    with open(REPOS_CONF, 'w') as f:
        repos_conf.write(f)
    for r in to_remove:
        if os.path.exists(os.path.join(reposdir, r)):
            shutil.rmtree(os.path.join(reposdir, r))
    local_repos = frozenset(repos_conf.sections())

    # 4. sync all repos
    print('* syncing repositories')
    jobs = []
    syncman = TaskManager(MAX_SYNC_JOBS, log)
    for r in sorted(local_repos):
        # pmaint is fast but fails most of the time...
        if can_pmaint(repos_conf, r):
            syncman.add(r, ['pmaint', 'sync', r])
        else:
            if not os.path.exists(os.path.join(reposdir, r)):
                os.mkdir(os.path.join(reposdir, r))
            syncman.add(r, ['portage-sync.py', r])

    # 5. check for sync failures
    to_readd = []
    for r, st in syncman.wait():
        if st == 0:
            log[r].status('Sync succeeded')
            states[r]['x-state'] = State.GOOD
        else:
            log[r].status('Sync failed with %d' % st)
            if r in existing_repos:
                log[r].status('Will try to re-create')
                if os.path.exists(os.path.join(reposdir, r)):
                    shutil.rmtree(os.path.join(reposdir, r))
                    os.mkdir(os.path.join(reposdir, r))
                to_readd.append(r)
            else:
                states[r]['x-state'] = State.SYNC_FAIL
                repos_conf.remove_section(r)

    # 6. remove local checkouts and sync again
    for r in sorted(to_readd):
        syncman.add(r, ['portage-sync.py', r])

    for r, st in syncman.wait():
        if st == 0:
            log[r].status('Sync succeeded after re-adding')
            states[r]['x-state'] = State.GOOD
        else:
            log[r].status('Sync failed again with %d, removing' % st)
            states[r]['x-state'] = State.SYNC_FAIL
            if os.path.exists(os.path.join(reposdir, r)):
                shutil.rmtree(os.path.join(reposdir, r))
            repos_conf.remove_section(r)

    with open(REPOS_CONF, 'w') as f:
        repos_conf.write(f)
    local_repos = frozenset(repos_conf.sections())

    # 7. check all added repos for invalid metadata:
    # - correct & matching repo_name (otherwise mischief will happen)
    # - correct masters= (otherwise pkgcore will fail)
    # - possibly other stuff causing pkgcore to fail hard

    import pkgcore.config

    pkgcore_config = pkgcore.config.load_config()
    for r in sorted(local_repos):
        repo_path = os.path.join(reposdir, r)
        config_sect = pkgcore_config.collapse_named_section(repo_path)
        raw_repo = config_sect.config['raw_repo'].instantiate()

        p_repo_id = raw_repo.repo_id
        p_masters = raw_repo.masters
        if raw_repo.is_empty:
            log[r].status('Empty repository, removing')
            states[r]['x-state'] = State.EMPTY
        elif not p_repo_id:
            log[r].status('Missing repo_name, removing')
            states[r]['x-state'] = State.MISSING_REPO_NAME
        elif p_repo_id != r:
            log[r].status('Conflicting repo_name, removing ("%s" in repo_name, "%s" on list)' % (p_repo_id, r))
            states[r]['x-state'] = State.CONFLICTING_REPO_NAME
            states[r]['x-repo-name'] = p_repo_id
        elif p_masters is None:
            log[r].status('Missing masters!')
            states[r]['x-state'] = State.MISSING_MASTERS
        else:
            for m in p_masters:
                if m not in remote_repos:
                    log[r].status('Invalid/unavailable master = %s, removing' % m)
                    states[r]['x-state'] = State.INVALID_MASTERS

        if states[r]['x-state'] in (State.GOOD, State.MISSING_MASTERS):
            # we check this since failure to instantiate a repo will
            # prevent pkgcore from operating further
            try:
                pkgcore_repo = config_sect.instantiate()
            except Exception:
                log[r].status('Invalid metadata, removing: %s' % str(e))
                states[r] = State.INVALID_METADATA

        if states[r]['x-state'] not in (State.GOOD, State.MISSING_MASTERS):
            shutil.rmtree(os.path.join(reposdir, r))
            repos_conf.remove_section(r)

    with open(REPOS_CONF, 'w') as f:
        repos_conf.write(f)
    local_repos = frozenset(repos_conf.sections())

    # 8. regen caches for all repos
    regenman = TaskManager(MAX_REGEN_JOBS, log)
    for r in sorted(local_repos):
        regenman.add(r, ['pmaint', 'regen', '-t', REGEN_THREADS, r])

    for r, st in regenman.wait():
        if st == 0:
            log[r].status('Cache regenerated successfully')
        else:
            log[r].status('Cache regen failed with %d' % st)
            # don't override higher priority issues here
            if states[r]['x-state'] == State.GOOD:
                states[r]['x-state'] = State.BAD_CACHE

    log.write_summary(states)

    # 9. run pkgcheck
    pkgcheckman = TaskManager(MAX_PCHECK_JOBS, log)
    for r in sorted(local_repos):
        pkgcheckman.add(r, ['pkgcheck', '-r', repos_conf.get(r, 'location'),
            '--reporter=FancyReporter',
            '--color=yes',
            '--profile-disable-dev',
            '--profile-disable-deprecated',
            '--profile-disable-exp',
            '*/*'])

    for r, st in pkgcheckman.wait():
        if st == 0:
            log[r].status('pkgcheck ran successfully')
        else:
            # shouldn't happen really
            log[r].status('pkgcheck failed with %d' % st)


if __name__ == '__main__':
    main()
