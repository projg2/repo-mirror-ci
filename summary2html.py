#!/usr/bin/env python

import datetime
import json
import os.path

with open('summary.json') as f:
    repos = json.load(f)

print('''
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
    if os.path.isfile('%s.html' % r):
        r = '<a href="%s.html">%s</a>' % (r, r)
    elif os.path.isfile('%s.txt' % r):
        r = '<a href="%s.txt">%s</a>' % (r, r)
    print('        <tr class="%s"><td>%s</td><td>%s</td>\n'
            % (s, r, status_mapping[s]))

print('''
    </table>

    <address>Generated on %s</address>
</body>
</html>
''' % datetime.datetime.utcnow().strftime('%F %T UTC'))