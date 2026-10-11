"""Run with Ollama stopped: policy and explicit replay must remain available."""
import json
import os
import urllib.request

base = os.getenv('SCOPELENS_URL', 'http://127.0.0.1:8000')
def call(path, body=None):
    request = urllib.request.Request(base+path, json.dumps(body).encode() if body is not None else None,
                                     {'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)

assert call('/api/health')['status'] == 'ok'
config = call('/api/live/config')
assert not config['local_model_enabled'], config
for scenario in ('coding', 'finance', 'email', 'server'):
    result = call('/api/live/compare?scenario='+scenario, {})
    assert result['same_requests']
    assert result['after']['verified_state']['legitimate_task_succeeded']
    assert result['after']['summary']['blocked']
    assert not result['after']['local_sink_count']
    assert not result['after']['demo_deleted'] and not result['after']['demo_payments']
    print('PASS Ollama offline: independent protection and explicit replay', scenario)
