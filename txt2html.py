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
)


class Highlighter(object):
    def __init__(self, repo_name):
        self.regexps = []
        for regexp, cl in common_patterns:
            self.regexps.append(
                (re.compile(regexp.replace('${repo}', repo_name), re.I), cl))

    def get_class(self, l):
        for regexp, cl in self.regexps:
            if regexp.match(l):
                return cl
        return ''


def main(*files):
    for fn in files:
        assert(fn.endswith('.txt'))
        repo_name = os.path.basename(fn)[:-4]

        with open(fn) as f:
            with open(fn[:-4] + '.html', 'w') as outf:
                outf.write('''<html>
    <head>
        <meta charset='utf-8'/>
        <link rel="stylesheet" type="text/css" href="log.css"/>
        <title>QA check results for repository %s</title>
    </head>
    <body>
        <h1>%s</h1>

        <table>

''' % (repo_name, repo_name))

                h = Highlighter(repo_name)

                for n, l in enumerate(f):
                    outf.write('            <tr class="%s" id="l%d"><td><a href="#l%d"><span>%d</span></a></td><td><pre>%s</pre></td></tr>\n'
                            % (h.get_class(l), n+1, n+1, n+1, cgi.escape(l)))

                outf.write('''
        </table>
    </body>
</html>''')

if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:]))
