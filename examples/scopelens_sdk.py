"""Dependency-free Python middleware for ScopeLens local sandbox tools."""
import json
import urllib.request

class ScopeLens:
    def __init__(self, policy, url='http://127.0.0.1:8000'):
        self.url = url.rstrip('/')
        session = self._post('/api/gateway/sessions', {'policy': policy})
        self.id, self.token = session['id'], session['token']

    def _post(self, path, body):
        headers = {'Content-Type': 'application/json'}
        if hasattr(self, 'token'):
            headers['Authorization'] = 'Bearer ' + self.token
        request = urllib.request.Request(self.url+path, json.dumps(body).encode(), headers)
        with urllib.request.urlopen(request, timeout=15) as response:
            return json.load(response)

    def call(self, tool, target, untrusted=False):
        return self._post(f'/api/gateway/sessions/{self.id}/tools',
                          {'tool': tool, 'target': target, 'untrusted': untrusted})

if __name__ == '__main__':
    gateway = ScopeLens({'job': 'Review project', 'tools': ['read_file'],
                        'resources': ['/workspace/github-project/**'],
                        'forbidden': ['/secrets/**']})
    for path in ['/workspace/github-project/app.py', '/secrets/demo_credentials.txt']:
        result = gateway.call('read_file', path)
        print(result['event']['decision'], path, result['state'])
