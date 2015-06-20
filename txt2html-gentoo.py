#!/usr/bin/env python

import cgi
import datetime
import os.path
import re
import sys


common_patterns = (
    ("NonsolvableDeps:", 'err'),
    ("IUSEMetadataReport:", 'err'),
    ("LicenseMetadataReport:", 'err'),
    ("VisibilityReport:", 'err'),
    ("MetadataError:", 'warn'),
    ("DroppedKeywordsReport:", 'warn'),
    ("TreeVulnerabilitiesReport:", 'warn'),
    ("DescriptionReport:", 'warn'),
    ("UnusedLocalFlagsReport:", 'warn'),
    ("CategoryMetadataXmlCheck:", 'warn'),
    ("PackageMetadataXmlCheck:", 'warn'),
    ("PkgDirReport:", 'warn'),
    ("UnusedGlobalFlagsResult:", 'warn'),
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


def main(repo_path, *files):
    h = Highlighter()
    results = {}

    menu = ''

    with open(os.path.join(repo_path, 'metadata', 'timestamp.x')) as f:
        ts = int(f.read().split()[0])

    for fn in sorted(files, key=ci_key):
        assert(fn.endswith('.txt'))

        with open(fn) as f:
            lines = {
                'warn': [],
                'err': [],
            }
            descs = {
                'warn': 'Warnings',
                'err': 'Errors',
            }
            max_cl = 'good'
            for i, l in enumerate(f):
                cl = h.get_class(l)
                for x in cl.split():
                    lines[x].append(i + 1)
                    if max_cl == 'good':
                        max_cl = x
                    elif max_cl == 'warn' and x == 'err':
                        max_cl = x

            data = ''
            for k, v in lines.items():
                if v:
                    data += '        <div class="lines %s">\n            <p>%s:</p>\n            <ol>\n' % (k, descs[k])
                    for l in v:
                        data += '                <li><a href="#l%d">%d</a></li>\n' % (l, l)
                    data += '            </ol>\n        </div>\n'

            results[fn] = data

            menu += ('            <li class="%s"><a href="%s">%s</a></li>\n'
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
        <ol class="menu">
%s
        </ol>

        %s

        <table class="log">

''' % (fn[:-4], menu, results[fn]))

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

        <address>Generated based on results from %s</address>
    </body>
</html>''' % datetime.datetime.utcfromtimestamp(ts).strftime('%F %T UTC'))

if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:]))
