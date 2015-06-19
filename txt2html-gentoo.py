#!/usr/bin/env python

import cgi
import os.path
import re
import sys


common_patterns = (
    ("NonsolvableDeps", 'err'),
    ("IUSEMetadataReport", 'err'),
    ("LicenseMetadataReport", 'err'),
    ("VisibilityReport", 'err'),
)


class Highlighter(object):
    def __init__(self):
        self.regexps = []
        for regexp, cl in common_patterns:
            self.regexps.append(
                (re.compile(regexp, re.I), cl))

    def get_class(self, l):
        for regexp, cl in self.regexps:
            if regexp.search(l):
                return cl
        return ''


def ci_key(x):
    assert(x.endswith('.txt'))
    x = x[:-4]
    if x == 'global':
        return 0
    else:
        return int(x) + 1


def main(*files):
    h = Highlighter()
    results = {}

    menu = ''

    for fn in sorted(files, key=ci_key):
        assert(fn.endswith('.txt'))

        with open(fn) as f:
            max_cl = 'good'
            for l in f:
                cl = h.get_class(l)
                if 'warn' in cl.split() and max_cl != 'err':
                    max_cl = 'warn'
                elif 'err' in cl.split():
                    max_cl = 'err'
                    break
            menu += ('                <td class="%s"><a href="%s">%s</a></td>\n'
                    % (max_cl, fn[:-4] + '.html', fn[:-4]))

    for fn in files:
        assert(fn.endswith('.txt'))

        with open(fn) as f:
            with open(fn[:-4] + '.html', 'w') as outf:
                outf.write('''<!DOCTYPE html>
<html>
    <head>
        <meta charset='utf-8'/>
        <link rel="stylesheet" type="text/css" href="log.css"/>
        <title>QA check results for repository gentoo [%s]</title>
    </head>
    <body>
        <table class="menu">
            <tr>
%s
            </tr>
        </table>

        <table class="log">

''' % (fn[:-4], menu))

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
