"""Check that redacted evidence survives a separately performed backend restart."""
import json
import sys
import urllib.request
from pathlib import Path

with urllib.request.urlopen('http://127.0.0.1:8000/api/gateway/proof', timeout=15) as response:
    report = json.load(response)
path = Path('/tmp/scopelens-persistence-check.json')
if sys.argv[1:] == ['before']:
    assert report['events'] and report['sessions']
    path.write_text(json.dumps({'event': report['events'][0]['id'], 'session': report['sessions'][0]['id']}))
    print('Recorded persistent event and session IDs')
else:
    expected = json.loads(path.read_text())
    assert any(e['id'] == expected['event'] for e in report['events'])
    assert any(s['id'] == expected['session'] for s in report['sessions'])
    print('PASS SQLite evidence and redacted session history survived backend restart')
