#!/usr/bin/env python

import cgi
import os.path
import re
import sys


common_patterns = (
    ("Repository '${repo}' is missing masters attribute", 'warn'),
    ("WARNING:pkgcore:repository at .* named '${repo}', doesn't specify masters", 'warn'),
    (" [*] Sync failed with", 'err'),
    ("!!! ERROR: .* failed.", 'err'),
    ("!!! The die message:", 'err'),
    ("caught exception", 'err'),
    ("failed sourcing ebuild", 'err'),
)


class Highlighter(object):
    def __init__(self, repo_name):
        self.regexps = []
        for regexp, cl in common_patterns:
            self.regexps.append(
                (re.compile(regexp.replace('${repo}', repo_name), re.I), cl))

    def get_class(self, l):
        for regexp, cl in self.regexps:
            if regexp.search(l):
                return cl
        return ''


def main(*files):
    for fn in files:
        assert(fn.endswith('.txt'))
        repo_name = os.path.basename(fn)[:-4]

        with open(fn) as f:
            with open(fn[:-4] + '.html', 'w') as outf:
                outf.write('''<!DOCTYPE html>
<html>
    <head>
        <meta charset='utf-8'/>
        <link rel="stylesheet" type="text/css" href="log.css"/>
        <title>QA check results for repository %s</title>
    </head>
    <body>
        <h1>%s</h1>

        <table class="log">

''' % (repo_name, repo_name))

                h = Highlighter(repo_name)

                for n, l in enumerate(f):
                    cl = h.get_class(l)
                    if 'warn' in cl.split():
                        wtag = '<td>[WARN]</td>'
                    elif 'err' in cl.split():
                        wtag = '<td>[FATAL]</td>'
                    else:
                        wtag = ''
                    outf.write('            <tr class="%s" id="l%d"><td><a href="#l%d"><span>%d</span></a></td><td><pre>%s</pre></td>%s</tr>\n'
                            % (cl, n+1, n+1, n+1, cgi.escape(l), wtag))

                outf.write('''
        </table>
    </body>
</html>''')

if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:]))
