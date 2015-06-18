#!/usr/bin/env python

import datetime
import json
import os
import os.path
import sys


def main(summary_path, output_path = None):
    with open(summary_path) as f:
        repos = json.load(f)
        st_res = os.fstat(f.fileno())
    if output_path is None:
        output_path = os.path.join(os.path.dirname(summary_path), 'index.html')
    res_dir = os.path.dirname(output_path)

    with open(output_path, 'w') as outf:
        outf.write('''
        <html>
        <head>
            <meta charset='utf-8'/>
            <link rel='stylesheet' type='text/css' href='repo-status.css'/>
            <title>Repository QA check results</title>
        </head>
        <body>
            <table>
                <tr><th>Repository</th><th>Status</th></tr>
        ''')

        status_mapping = {
            'GOOD': 'all good!',
            'BAD_CACHE': 'cache regen failed',
            'INVALID_METADATA': 'invalid repository metadata (wrong masters= most likely)',
            'EMPTY': 'repository empty',
            'SYNC_FAIL': 'sync failed for repository',
            'UNSUPPORTED': 'repository VCS unsupported',
            'REMOVED': 'repository removed',
        }

        for r, s in sorted(repos.items()):
            if os.path.isfile(os.path.join(res_dir, '%s.html' % r)):
                r = '<a href="%s.html">%s</a>' % (r, r)
            elif os.path.isfile(os.path.join(res_dir, '%s.txt' % r)):
                r = '<a href="%s.txt">%s</a>' % (r, r)
            outf.write('        <tr class="%s"><td>%s</td><td>%s</td>\n'
                    % (s, r, status_mapping[s]))

        outf.write('''
            </table>

            <address>Generated based on results from %s</address>
        </body>
        </html>
        ''' % datetime.datetime.utcfromtimestamp(st_res.st_mtime).strftime('%F %T UTC'))


if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:]))
